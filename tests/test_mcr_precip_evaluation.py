import numpy as np

from mazu_saudi.mcr_precip.evaluation import (
    binary_metrics,
    risk_coverage_curve,
    select_csi_threshold,
)


def test_perfect_probabilities_have_perfect_event_scores():
    metrics = binary_metrics([0, 0, 1, 1], [0.01, 0.1, 0.9, 0.99])
    assert metrics["pr_auc"] == 1
    assert metrics["csi"] == 1
    assert metrics["pod"] == 1
    assert metrics["far"] == 0
    assert metrics["brier"] < 0.01


def test_risk_coverage_rejects_high_uncertainty_error_last():
    coverage, risk = risk_coverage_curve(
        [0, 1, 1], [0.1, 0.8, 0.2], [0.1, 0.2, 0.9]
    )
    assert np.allclose(coverage, [1 / 3, 2 / 3, 1])
    assert np.allclose(risk, [0, 0, 1 / 3])


def test_csi_threshold_is_selected_from_explicit_validation_grid():
    threshold, metrics = select_csi_threshold(
        [0, 0, 1, 1],
        [0.1, 0.4, 0.45, 0.9],
        thresholds=[0.3, 0.5, 0.7],
    )
    assert threshold == 0.3
    assert metrics["csi"] == 2 / 3
