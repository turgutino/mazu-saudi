"""Probability calibration (初步设计.md 第3节: 校准与风险决策层).

A real implementation would fit an isotonic/Platt scaling curve against
observed outcomes so ``calibrated_probability`` better reflects true
frequencies than the raw model output. v1 ships no historical verification
data, so ``calibrate`` is an identity function — it exists purely so
``RawPrediction.probability`` and ``PredictionResult.calibrated_probability``
are never silently conflated by callers.

TODO(v2): replace with a fitted calibration curve per model_id/hazard once
verification data is available.
"""

from __future__ import annotations


def calibrate(probability: float, hazard: str, model_id: str) -> float:
    """Return the calibrated probability for a given raw probability.

    ``hazard`` and ``model_id`` are accepted (and currently unused) so the
    call site is already correct once a real per-hazard/per-model curve is
    plugged in here.
    """

    return round(probability, 4)
