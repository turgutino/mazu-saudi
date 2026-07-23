"""MCR-Precip: mechanism-constrained mixture of propagation experts."""

from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.nn import functional as F

from .contracts import MCRPrecipBatch, MCRPrecipOutput
from .priors import AVAILABILITY_FEATURES, MECHANISM_FEATURES, expert_availability


@dataclass(frozen=True)
class MCRPrecipConfig:
    dynamic_channels: int
    static_channels: int
    hidden_channels: int = 32
    mechanism_dim: int = len(MECHANISM_FEATURES)
    availability_dim: int = len(AVAILABILITY_FEATURES)
    quantile_levels: tuple[float, ...] = (0.1, 0.5, 0.9)
    router_temperature: float = 1.0
    max_advection_pixels: float = 2.0

    def as_dict(self) -> dict:
        return asdict(self)


def _block(in_channels: int, out_channels: int, dilation: int = 1) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, 3, padding=dilation, dilation=dilation),
        nn.GroupNorm(1, out_channels),
        nn.GELU(),
    )


class AdvectionExpert(nn.Module):
    def __init__(self, channels: int, max_pixels: float):
        super().__init__()
        self.max_pixels = max_pixels
        self.refine = _block(channels, channels)

    def forward(self, last: torch.Tensor, mechanism: torch.Tensor) -> torch.Tensor:
        b, _, h, w = last.shape
        theta = last.new_zeros((b, 2, 3))
        theta[:, 0, 0] = 1
        theta[:, 1, 1] = 1
        # affine_grid translation is normalized to [-1,1]. Reverse the motion
        # to sample the upstream source location for a forward forecast.
        theta[:, 0, 2] = -torch.tanh(mechanism[:, 0]) * 2 * self.max_pixels / max(w - 1, 1)
        theta[:, 1, 2] = -torch.tanh(mechanism[:, 1]) * 2 * self.max_pixels / max(h - 1, 1)
        grid = F.affine_grid(theta, last.shape, align_corners=True)
        transported = F.grid_sample(last, grid, mode="bilinear", padding_mode="border", align_corners=True)
        return self.refine(transported)


class ConvectionExpert(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.local = _block(channels, channels)
        self.multiscale = _block(channels, channels, dilation=2)
        self.condition = nn.Linear(2, channels)

    def forward(self, context: torch.Tensor, mechanism: torch.Tensor) -> torch.Tensor:
        forcing = torch.sigmoid(self.condition(mechanism[:, 3:5]))[:, :, None, None]
        peaks = F.max_pool2d(context, 3, stride=1, padding=1)
        return self.local(context) + forcing * self.multiscale(peaks)


class OrographicExpert(nn.Module):
    def __init__(self, channels: int, static_channels: int):
        super().__init__()
        self.terrain = _block(static_channels + 2, channels)
        self.combine = _block(2 * channels, channels)

    def forward(self, context: torch.Tensor, static: torch.Tensor, mechanism: torch.Tensor) -> torch.Tensor:
        elevation = static[:, :1]
        dx = F.pad(elevation[..., 1:] - elevation[..., :-1], (0, 1, 0, 0))
        dy = F.pad(elevation[..., 1:, :] - elevation[..., :-1, :], (0, 0, 0, 1))
        terrain = self.terrain(torch.cat((static, dx, dy), dim=1))
        upslope = torch.relu(mechanism[:, 5:6])[:, :, None, None]
        return self.combine(torch.cat((context, terrain * (1 + upslope)), dim=1))


class PersistenceExpert(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.decay_rate = nn.Parameter(torch.tensor(0.12))
        self.refine = _block(2 * channels, channels)

    def forward(self, sequence: torch.Tensor, lead_hours: torch.Tensor) -> torch.Tensor:
        last = sequence[:, -1]
        mean = sequence.mean(dim=1)
        rate = F.softplus(self.decay_rate)
        decay = torch.exp(-rate * lead_hours.float() / 6.0)[:, None, None, None]
        return self.refine(torch.cat((last, mean), dim=1)) * decay


class MCRPrecip(nn.Module):
    """Four-expert model whose routing variables are geographically portable."""

    expert_names = ("advection", "convection", "orography", "persistence")

    def __init__(self, config: MCRPrecipConfig):
        super().__init__()
        if config.static_channels < 1:
            raise ValueError("at least one static terrain channel is required")
        if any(left >= right for left, right in zip(config.quantile_levels, config.quantile_levels[1:])):
            raise ValueError("quantile_levels must be strictly increasing")
        self.config = config
        c = config.hidden_channels
        self.encoder = _block(config.dynamic_channels, c)
        self.experts = nn.ModuleList(
            (AdvectionExpert(c, config.max_advection_pixels), ConvectionExpert(c),
             OrographicExpert(c, config.static_channels), PersistenceExpert(c))
        )
        router_in = config.mechanism_dim + config.availability_dim + 1
        self.router = nn.Sequential(nn.Linear(router_in, c), nn.GELU(), nn.Linear(c, 4))
        self.occurrence_head = nn.Conv2d(c, 1, 1)
        self.quantile_head = nn.Conv2d(c, len(config.quantile_levels), 1)
        self.uncertainty_head = nn.Conv2d(c, 1, 1)

    def forward(self, batch: MCRPrecipBatch) -> MCRPrecipOutput:
        cfg = self.config
        batch.validate(cfg.mechanism_dim, cfg.availability_dim)
        b, t, c_in, h, w = batch.dynamic.shape
        encoded = self.encoder(batch.dynamic.reshape(b * t, c_in, h, w)).reshape(
            b, t, cfg.hidden_channels, h, w
        )
        last, context = encoded[:, -1], encoded.mean(dim=1)
        expert_features = torch.stack(
            (
                self.experts[0](last, batch.mechanism),
                self.experts[1](context, batch.mechanism),
                self.experts[2](context, batch.static, batch.mechanism),
                self.experts[3](encoded, batch.lead_hours),
            ),
            dim=1,
        )
        lead = (batch.lead_hours.float() / 6.0)[:, None]
        router_input = torch.cat((batch.mechanism, batch.availability, lead), dim=1)
        logits = self.router(router_input) / cfg.router_temperature
        gates = expert_availability(batch.availability).clamp_min(1e-6)
        router_weights = torch.softmax(logits + gates.log(), dim=1)
        fused = (expert_features * router_weights[:, :, None, None, None]).sum(dim=1)
        raw_q = self.quantile_head(fused)
        increments = F.softplus(raw_q)
        quantiles = torch.cumsum(increments, dim=1)
        return MCRPrecipOutput(
            occurrence_logits=self.occurrence_head(fused),
            quantiles=quantiles,
            uncertainty=F.softplus(self.uncertainty_head(fused)) + 1e-6,
            router_weights=router_weights,
            expert_features=expert_features,
        )
