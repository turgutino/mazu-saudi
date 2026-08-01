"""Explicit calibration outcome contract (初步设计.md 第3节).

A real implementation would fit an isotonic/Platt scaling curve against
independent observed outcomes. The current system has no such fitted
artifact, so ``calibrate`` returns the unchanged score together with
``method=none`` and ``is_calibrated=False``. Callers must not label this value
as a calibrated hazard probability.

TODO(v2): replace with a fitted calibration curve per model_id/hazard once
verification data is available.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationResult:
    score: float
    method: str
    is_calibrated: bool


def calibrate(probability: float, hazard: str, model_id: str) -> CalibrationResult:
    """Return the current score and an honest calibration status.

    ``hazard`` and ``model_id`` are accepted (and currently unused) so the
    call site is already correct once a real per-hazard/per-model curve is
    plugged in here.
    """

    return CalibrationResult(
        score=round(probability, 4),
        method="none",
        is_calibrated=False,
    )
