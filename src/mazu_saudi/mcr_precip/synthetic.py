"""Small deterministic generator for engineering smoke tests only."""

import torch

from .contracts import MCRPrecipBatch
from .priors import applicability_prior


def make_synthetic_batch(
    batch_size: int = 4,
    history: int = 4,
    dynamic_channels: int = 5,
    static_channels: int = 2,
    height: int = 12,
    width: int = 12,
    seed: int = 7,
) -> tuple[MCRPrecipBatch, torch.Tensor]:
    """Create physically suggestive tensors; never use these as paper evidence."""

    generator = torch.Generator().manual_seed(seed)
    dynamic = torch.randn(batch_size, history, dynamic_channels, height, width, generator=generator)
    yy, xx = torch.meshgrid(torch.linspace(-1, 1, height), torch.linspace(-1, 1, width), indexing="ij")
    terrain = (0.6 * xx + 0.4 * yy)[None, None].repeat(batch_size, 1, 1, 1)
    static = torch.cat((terrain, terrain.square()), dim=1)
    if static_channels != 2:
        static = torch.randn(batch_size, static_channels, height, width, generator=generator)
        static[:, :1] = terrain
    mechanism = torch.rand(batch_size, 8, generator=generator)
    mechanism[:, :2] = mechanism[:, :2] * 2 - 1
    mechanism[:, 5] = mechanism[:, 5] * 2 - 1
    availability = torch.ones(batch_size, 3)
    lead_hours = torch.tensor([1, 3, 6], dtype=torch.long).repeat((batch_size + 2) // 3)[:batch_size]
    signal = dynamic[:, -1, :1] + 0.5 * dynamic[:, -2, :1] + 0.4 * terrain
    rainfall = torch.relu(signal) * (2 + 4 * mechanism[:, 4, None, None, None])
    occurrence = (rainfall > rainfall.flatten(1).quantile(0.85, dim=1)[:, None, None, None]).float()
    batch = MCRPrecipBatch(dynamic, static, mechanism, availability, lead_hours, occurrence, rainfall)
    return batch, applicability_prior(mechanism)
