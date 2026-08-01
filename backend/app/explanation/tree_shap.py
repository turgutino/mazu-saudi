"""Verified local Tree SHAP attribution for binary tree classifiers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TreeShapResult:
    values: dict[str, float]
    base_value: float
    model_output: float
    method: str = "tree_shap"
    output_scale: str = "raw_log_odds"


class TreeShapAttributor:
    """Explain one binary classifier on its raw margin/log-odds scale."""

    def __init__(self, estimator, feature_names: list[str]):
        from shap import TreeExplainer

        self._estimator = estimator
        self._feature_names = tuple(feature_names)
        self._explainer = TreeExplainer(
            estimator,
            feature_perturbation="tree_path_dependent",
            model_output="raw",
        )

    def explain(self, row: np.ndarray) -> TreeShapResult:
        if row.shape != (1, len(self._feature_names)):
            raise ValueError(
                f"Expected one row with {len(self._feature_names)} features, got {row.shape}"
            )

        explanation = self._explainer(row, check_additivity=True)
        values = np.asarray(explanation.values, dtype="float64")
        base_values = np.asarray(explanation.base_values, dtype="float64")

        # SHAP may expose a class axis for some binary tree implementations.
        if values.ndim == 3:
            values = values[:, :, -1]
        if base_values.ndim == 2:
            base_values = base_values[:, -1]

        shap_values = values[0]
        base_value = float(base_values.reshape(-1)[0])
        model_output = float(np.asarray(self._estimator.decision_function(row)).reshape(-1)[0])
        reconstructed = base_value + float(shap_values.sum())
        if not np.isclose(reconstructed, model_output, rtol=1e-7, atol=1e-7):
            raise RuntimeError(
                "Tree SHAP additivity check failed: "
                f"base + contributions={reconstructed}, model output={model_output}"
            )

        return TreeShapResult(
            values={
                name: round(float(value), 6)
                for name, value in zip(self._feature_names, shap_values, strict=True)
            },
            base_value=round(base_value, 6),
            model_output=round(model_output, 6),
        )
