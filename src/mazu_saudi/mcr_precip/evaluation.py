"""Rare-event probability and selective-prediction metrics."""

import numpy as np


def _finite_binary(y_true, probability):
    y = np.asarray(y_true, dtype=float).ravel()
    p = np.asarray(probability, dtype=float).ravel()
    valid = np.isfinite(y) & np.isfinite(p)
    y, p = y[valid], np.clip(p[valid], 1e-7, 1 - 1e-7)
    if y.size == 0 or not np.isin(y, (0, 1)).all():
        raise ValueError("metrics require at least one finite binary target")
    return y.astype(int), p


def average_precision(y_true, probability) -> float:
    """Non-interpolated PR-AUC (average precision)."""

    y, p = _finite_binary(y_true, probability)
    positives = y.sum()
    if positives == 0:
        return float("nan")
    order = np.argsort(-p, kind="stable")
    ranked = y[order]
    precision = np.cumsum(ranked) / np.arange(1, ranked.size + 1)
    return float(precision[ranked == 1].sum() / positives)


def expected_calibration_error(y_true, probability, bins: int = 10) -> float:
    y, p = _finite_binary(y_true, probability)
    edges = np.linspace(0, 1, bins + 1)
    total = y.size
    error = 0.0
    for index in range(bins):
        right_closed = index == bins - 1
        selected = (p >= edges[index]) & ((p <= edges[index + 1]) if right_closed else (p < edges[index + 1]))
        if selected.any():
            error += selected.sum() / total * abs(p[selected].mean() - y[selected].mean())
    return float(error)


def binary_metrics(y_true, probability, threshold: float = 0.5, bins: int = 10) -> dict[str, float]:
    y, p = _finite_binary(y_true, probability)
    pred = p >= threshold
    tp = int(((y == 1) & pred).sum())
    fp = int(((y == 0) & pred).sum())
    fn = int(((y == 1) & ~pred).sum())
    csi_denominator = tp + fp + fn
    pod_denominator = tp + fn
    far_denominator = tp + fp
    return {
        "pr_auc": average_precision(y, p),
        "csi": tp / csi_denominator if csi_denominator else float("nan"),
        "pod": tp / pod_denominator if pod_denominator else float("nan"),
        "far": fp / far_denominator if far_denominator else float("nan"),
        "brier": float(np.mean((p - y) ** 2)),
        "nll": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
        "ece": expected_calibration_error(y, p, bins=bins),
    }


def risk_coverage_curve(y_true, probability, uncertainty) -> tuple[np.ndarray, np.ndarray]:
    """Return error risk when retaining samples from most to least certain."""

    y, p = _finite_binary(y_true, probability)
    u = np.asarray(uncertainty, dtype=float).ravel()
    if u.size != np.asarray(probability).size:
        raise ValueError("uncertainty and probability must have identical size")
    valid = np.isfinite(np.asarray(y_true, dtype=float).ravel()) & np.isfinite(np.asarray(probability, dtype=float).ravel())
    u = u[valid]
    if not np.isfinite(u).all():
        raise ValueError("uncertainty must be finite for observable samples")
    order = np.argsort(u, kind="stable")
    errors = ((p[order] >= 0.5) != y[order]).astype(float)
    retained = np.arange(1, y.size + 1)
    return retained / y.size, np.cumsum(errors) / retained
