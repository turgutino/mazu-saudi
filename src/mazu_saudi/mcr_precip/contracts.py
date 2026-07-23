"""Stable tensor contracts shared by data adapters, models, and evaluation."""

from dataclasses import dataclass
from typing import Optional

import torch


@dataclass
class MCRPrecipBatch:
    """A causal forecast batch.

    Dynamic fields have shape ``[batch, history, channel, height, width]``;
    static fields have shape ``[batch, channel, height, width]``.  Mechanism
    state deliberately excludes region identifiers and absolute coordinates.
    """

    dynamic: torch.Tensor
    static: torch.Tensor
    mechanism: torch.Tensor
    availability: torch.Tensor
    lead_hours: torch.Tensor
    occurrence: Optional[torch.Tensor] = None
    rainfall: Optional[torch.Tensor] = None

    def validate(self, mechanism_dim: int, availability_dim: int) -> None:
        if self.dynamic.ndim != 5:
            raise ValueError("dynamic must have shape [B,T,C,H,W]")
        if self.static.ndim != 4:
            raise ValueError("static must have shape [B,S,H,W]")
        b, _, _, h, w = self.dynamic.shape
        if self.static.shape[0] != b or self.static.shape[-2:] != (h, w):
            raise ValueError("static and dynamic grids must agree")
        if self.mechanism.shape != (b, mechanism_dim):
            raise ValueError(f"mechanism must have shape [B,{mechanism_dim}]")
        if self.availability.shape != (b, availability_dim):
            raise ValueError(f"availability must have shape [B,{availability_dim}]")
        if self.lead_hours.shape != (b,):
            raise ValueError("lead_hours must have shape [B]")
        if not torch.isin(self.lead_hours, self.lead_hours.new_tensor([1, 3, 6])).all():
            raise ValueError("lead_hours must contain only 1, 3, or 6")
        if not torch.isfinite(self.dynamic).all() or not torch.isfinite(self.static).all():
            raise ValueError("inputs must be finite; encode missingness with availability")
        if ((self.availability < 0) | (self.availability > 1)).any():
            raise ValueError("availability must lie in [0,1]")
        for name, target in (("occurrence", self.occurrence), ("rainfall", self.rainfall)):
            if target is not None and target.shape != (b, 1, h, w):
                raise ValueError(f"{name} must have shape [B,1,H,W]")

    def to(self, device: torch.device | str) -> "MCRPrecipBatch":
        values = {
            name: value.to(device) if isinstance(value, torch.Tensor) else value
            for name, value in vars(self).items()
        }
        return MCRPrecipBatch(**values)


@dataclass
class MCRPrecipOutput:
    occurrence_logits: torch.Tensor
    quantiles: torch.Tensor
    uncertainty: torch.Tensor
    router_weights: torch.Tensor
    expert_features: torch.Tensor

    @property
    def occurrence_probability(self) -> torch.Tensor:
        return torch.sigmoid(self.occurrence_logits)
