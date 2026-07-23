#!/usr/bin/env python3
"""Run an engineering-only MCR-Precip training smoke test."""

import argparse
from datetime import datetime, timezone

import torch

from mazu_saudi.mcr_precip.losses import LossConfig
from mazu_saudi.mcr_precip.model import MCRPrecip, MCRPrecipConfig
from mazu_saudi.mcr_precip.synthetic import make_synthetic_batch
from mazu_saudi.mcr_precip.training import save_bundle, train_step


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Output .pt model bundle")
    parser.add_argument("--steps", type=int, default=5)
    args = parser.parse_args()
    torch.manual_seed(7)
    batch, prior = make_synthetic_batch()
    model = MCRPrecip(MCRPrecipConfig(dynamic_channels=5, static_channels=2, hidden_channels=16))
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    metrics = {}
    for _ in range(args.steps):
        metrics = train_step(model, batch, optimizer, LossConfig(), prior)
    save_bundle(
        args.output,
        model,
        {
            "source_version": "synthetic-smoke-v1",
            "feature_contract": "mcr-precip-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scientific_evidence": False,
            "final_training_loss": metrics["total"],
        },
    )
    print(f"saved={args.output} total_loss={metrics['total']:.6f}")


if __name__ == "__main__":
    main()
