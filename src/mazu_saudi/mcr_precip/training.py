"""Minimal training and versioned artifact utilities."""

from dataclasses import asdict
from pathlib import Path
from typing import Any

import torch

from .contracts import MCRPrecipBatch
from .losses import LossConfig, total_loss
from .model import MCRPrecip, MCRPrecipConfig


def train_step(
    model: MCRPrecip,
    batch: MCRPrecipBatch,
    optimizer: torch.optim.Optimizer,
    loss_config: LossConfig = LossConfig(),
    routing_prior: torch.Tensor | None = None,
) -> dict[str, float]:
    model.train()
    optimizer.zero_grad(set_to_none=True)
    output = model(batch)
    loss, terms = total_loss(
        output, batch, model.config.quantile_levels, loss_config, routing_prior=routing_prior
    )
    if not torch.isfinite(loss):
        raise FloatingPointError("non-finite training loss")
    loss.backward()
    optimizer.step()
    return {name: float(value.detach()) for name, value in terms.items()}


@torch.no_grad()
def predict(model: MCRPrecip, batch: MCRPrecipBatch) -> dict[str, torch.Tensor]:
    model.eval()
    output = model(batch)
    return {
        "occurrence_probability": output.occurrence_probability,
        "quantiles": output.quantiles,
        "uncertainty": output.uncertainty,
        "router_weights": output.router_weights,
    }


def save_bundle(
    path: str | Path,
    model: MCRPrecip,
    metadata: dict[str, Any],
) -> None:
    required = {"source_version", "feature_contract", "created_at"}
    missing = required.difference(metadata)
    if missing:
        raise ValueError(f"metadata missing required fields: {sorted(missing)}")
    payload = {
        "format_version": 1,
        "model_config": model.config.as_dict(),
        "state_dict": model.state_dict(),
        "metadata": metadata,
    }
    torch.save(payload, Path(path))


def load_bundle(path: str | Path, map_location: str | torch.device = "cpu") -> tuple[MCRPrecip, dict]:
    payload = torch.load(Path(path), map_location=map_location, weights_only=False)
    if payload.get("format_version") != 1:
        raise ValueError("unsupported model bundle format")
    config_values = dict(payload["model_config"])
    config_values["quantile_levels"] = tuple(config_values["quantile_levels"])
    model = MCRPrecip(MCRPrecipConfig(**config_values))
    model.load_state_dict(payload["state_dict"])
    return model, payload["metadata"]
