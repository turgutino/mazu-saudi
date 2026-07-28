#!/usr/bin/env python3
"""Run the bounded Saudi 2025 HGB/MoE/MCR precipitation-proxy comparison."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import torch

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mazu_saudi.mcr_precip.evaluation import binary_metrics, select_csi_threshold
from mazu_saudi.mcr_precip.real_data import prepare_proxy_data
from mazu_saudi.mcr_precip.real_experiment import (
    NeuralExperimentConfig,
    evaluate_neural_variant,
    train_neural_variant,
)


REFERENCE_HGB = {
    "protocol": "legacy stride=2, Jan-Jun train, Jul-Dec test, threshold=0.5",
    "pr_auc": 0.08906247051431657,
    "csi": 0.07128292268479185,
    "pod": 0.10038286671452501,
    "far": 0.8026346741943072,
}


def _flatten(data, indices):
    x = data.dynamic[indices, 0].permute(0, 2, 3, 1).numpy().reshape(-1, data.dynamic.shape[2])
    y = data.occurrence[indices].numpy().reshape(-1)
    valid = np.isfinite(y)
    return x[valid], y[valid].astype(int)


def run_hgb(data, seed):
    from sklearn.ensemble import HistGradientBoostingClassifier

    train_x, train_y = _flatten(data, data.split.train)
    val_x, val_y = _flatten(data, data.split.validation)
    test_x, test_y = _flatten(data, data.split.test)
    model = HistGradientBoostingClassifier(
        max_iter=120,
        max_depth=6,
        learning_rate=0.08,
        class_weight="balanced",
        random_state=seed,
        early_stopping=True,
    )
    model.fit(train_x, train_y)
    val_probability = model.predict_proba(val_x)[:, 1]
    threshold, validation = select_csi_threshold(val_y, val_probability)
    started = time.perf_counter()
    test_probability = model.predict_proba(test_x)[:, 1]
    elapsed = time.perf_counter() - started
    return {
        "seed": seed,
        "threshold_source": "validation",
        "threshold": threshold,
        "validation": validation,
        "test": binary_metrics(test_y, test_probability, threshold),
        "test_observations": int(test_y.size),
        "test_positive_rate": float(test_y.mean()),
        "parameters": None,
        "cpu_inference_seconds": elapsed,
        "cpu_microseconds_per_grid_cell": elapsed * 1e6 / max(test_y.size, 1),
    }


def summarize(runs):
    metrics = ("pr_auc", "csi", "pod", "far", "brier", "nll", "ece")
    return {
        metric: {
            "mean": float(np.mean([run["test"][metric] for run in runs])),
            "std": float(np.std([run["test"][metric] for run in runs])),
        }
        for metric in metrics
    }


def render_report(result):
    lines = [
        "# MCR-Precip Saudi 2025 real-data proxy comparison",
        "",
        "> This is a 24-hour `flash_flood_risk>=2` proxy-label experiment, not an",
        "> independent flash-flood truth evaluation or an operational warning result.",
        "",
        f"- Generated: `{result['generated_at']}`",
        f"- Split: {result['protocol']['split']}",
        f"- Grid: stride {result['protocol']['stride']} ({result['protocol']['grid_shape']})",
        f"- Seeds: {result['protocol']['seeds']}",
        f"- Terrain available: {result['protocol']['terrain_available']}",
        "- Thresholds are selected on June validation data; July–December is test-only.",
        "",
        "| Model | PR-AUC | CSI | POD | FAR | Brier | ECE |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "hgb_matched": "HGB, matched inputs",
        "moe_unconstrained": "MoE, no mechanism prior",
        "mcr_prior": "MCR, mechanism prior",
    }
    for key, label in labels.items():
        summary = result["models"][key]["summary"]
        values = [summary[name]["mean"] for name in ("pr_auc", "csi", "pod", "far", "brier", "ece")]
        lines.append(f"| {label} | " + " | ".join(f"{value:.4f}" for value in values) + " |")
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "- The MCR run uses the applicability-prior constraint only; real-data",
        "  counterfactual training is not included in this bounded experiment.",
        "- Consolidated inputs lack vector wind, so advection direction is unavailable.",
        "- The historical HGB number is included as context only because it uses a",
        "  different stride and no independent validation threshold.",
        "- A gain is competition evidence only if it is stable across seeds and does",
        "  not trade lower PR-AUC/Brier reliability for a test-tuned operating point.",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "warning_demo" / "data" / "mazu_dataset.nc"))
    parser.add_argument("--orography-source")
    parser.add_argument("--output-dir", default=str(ROOT / "experiments" / "mcr_precip_2025_proxy"))
    parser.add_argument("--stride", type=int, default=4)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--hidden-channels", type=int, default=8)
    parser.add_argument("--batch-days", type=int, default=4)
    args = parser.parse_args()

    seeds = [int(value) for value in args.seeds.split(",") if value.strip()]
    data = prepare_proxy_data(args.dataset, args.orography_source, stride=args.stride)
    neural_config = NeuralExperimentConfig(
        hidden_channels=args.hidden_channels,
        epochs=args.epochs,
        batch_days=args.batch_days,
    )
    models = {"hgb_matched": {"runs": []}, "moe_unconstrained": {"runs": []}, "mcr_prior": {"runs": []}}
    for seed in seeds:
        models["hgb_matched"]["runs"].append(run_hgb(data, seed))
        for key, constrained in (("moe_unconstrained", False), ("mcr_prior", True)):
            model, training = train_neural_variant(
                data, constrained=constrained, seed=seed, config=neural_config, device="cpu"
            )
            evaluation = evaluate_neural_variant(
                model, data, batch_days=args.batch_days, device="cpu"
            )
            evaluation["training"] = training
            models[key]["runs"].append(evaluation)
    for model in models.values():
        model["summary"] = summarize(model["runs"])

    result = {
        "schema_version": "mcr-proxy-comparison-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scientific_evidence": "single-year-proxy-only",
        "task": "T+1 day flash_flood_risk>=2 proxy label",
        "protocol": {
            "split": "train through 2025-05-31; validation 2025-06; test 2025-07-01 onward",
            "stride": args.stride,
            "grid_shape": list(data.dynamic.shape[-2:]),
            "seeds": seeds,
            "features": list(data.feature_names),
            "terrain_available": data.terrain_available,
            "threshold_source": "validation",
            "test_tuned": False,
        },
        "legacy_hgb_context_only": REFERENCE_HGB,
        "models": models,
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "report.md").write_text(render_report(result), encoding="utf-8")
    print(render_report(result))


if __name__ == "__main__":
    main()
