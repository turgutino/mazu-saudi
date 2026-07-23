"""Losses for rare occurrence, intensity, routing, and counterfactual tests."""

from dataclasses import dataclass
from typing import Mapping

import torch
from torch.nn import functional as F

from .contracts import MCRPrecipBatch, MCRPrecipOutput


@dataclass(frozen=True)
class LossConfig:
    occurrence_weight: float = 1.0
    quantile_weight: float = 1.0
    prior_weight: float = 0.1
    counterfactual_weight: float = 0.1
    pos_weight: float = 1.0


def pinball_loss(prediction: torch.Tensor, target: torch.Tensor, levels: tuple[float, ...]) -> torch.Tensor:
    if prediction.shape[1] != len(levels):
        raise ValueError("prediction channel count must match quantile levels")
    valid = torch.isfinite(target)
    if not valid.any():
        return prediction.sum() * 0
    error = target - prediction
    q = prediction.new_tensor(levels)[None, :, None, None]
    loss = torch.maximum(q * error, (q - 1) * error)
    return loss.expand_as(prediction).masked_select(valid.expand_as(prediction)).mean()


def routing_kl(router_weights: torch.Tensor, prior: torch.Tensor) -> torch.Tensor:
    if router_weights.shape != prior.shape:
        raise ValueError("router weights and prior must have identical shapes")
    p = prior.clamp_min(1e-8)
    p = p / p.sum(dim=1, keepdim=True)
    q = router_weights.clamp_min(1e-8)
    return (p * (p.log() - q.log())).sum(dim=1).mean()


def directional_counterfactual_loss(
    base_weights: torch.Tensor,
    counterfactual_weights: torch.Tensor,
    expert_index: int,
    direction: str = "decrease",
    margin: float = 0.0,
) -> torch.Tensor:
    """Penalize a router response that contradicts a pre-registered direction."""

    delta = counterfactual_weights[:, expert_index] - base_weights[:, expert_index]
    if direction == "decrease":
        return F.relu(delta + margin).mean()
    if direction == "increase":
        return F.relu(-delta + margin).mean()
    raise ValueError("direction must be 'decrease' or 'increase'")


def total_loss(
    output: MCRPrecipOutput,
    batch: MCRPrecipBatch,
    quantile_levels: tuple[float, ...],
    config: LossConfig = LossConfig(),
    routing_prior: torch.Tensor | None = None,
    counterfactual_losses: Mapping[str, torch.Tensor] | None = None,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    if batch.occurrence is None or batch.rainfall is None:
        raise ValueError("occurrence and rainfall targets are required for training")
    valid_occurrence = torch.isfinite(batch.occurrence)
    if valid_occurrence.any():
        occurrence = F.binary_cross_entropy_with_logits(
            output.occurrence_logits.masked_select(valid_occurrence),
            batch.occurrence.masked_select(valid_occurrence),
            pos_weight=output.occurrence_logits.new_tensor(config.pos_weight),
        )
    else:
        occurrence = output.occurrence_logits.sum() * 0
    quantile = pinball_loss(output.quantiles, batch.rainfall, quantile_levels)
    prior = output.router_weights.sum() * 0
    if routing_prior is not None:
        prior = routing_kl(output.router_weights, routing_prior)
    counterfactual = output.router_weights.sum() * 0
    if counterfactual_losses:
        counterfactual = torch.stack(tuple(counterfactual_losses.values())).mean()
    terms = {
        "occurrence": occurrence,
        "quantile": quantile,
        "prior": prior,
        "counterfactual": counterfactual,
    }
    total = (
        config.occurrence_weight * occurrence
        + config.quantile_weight * quantile
        + config.prior_weight * prior
        + config.counterfactual_weight * counterfactual
    )
    terms["total"] = total
    return total, terms
