"""Model explanation (初步设计.md 第4节: 模型解释).

Turns a RawPrediction's ``important_features`` (per-indicator contributions
already computed by the ForecastModel, see models/rule_based_model.py) plus
the actual indicator values into the API-facing ``FeatureContribution`` list.

This is explicitly *not* SHAP — RuleBasedForecastModel's contributions are
plain linear-term outputs. If a real SHAP-explainable model is plugged in
later, only the ``important_features`` values change; this module's shape
stays the same.
"""

from __future__ import annotations

from app.data.indicator_provider import INDICATOR_SPECS
from app.domain.prediction import RawPrediction
from app.schemas.prediction import FeatureContribution


def build_feature_contributions(
    prediction: RawPrediction, indicators: dict[str, float]
) -> list[FeatureContribution]:
    """Rank indicators by |contribution| and format them as FeatureContribution.

    Only features with a known ``INDICATOR_SPECS`` entry are included: a real
    trained model's ``important_features`` (see models/joblib_model.py) uses
    raw NetCDF variable names (e.g. ``t2m_c``, ``pwat``) that have no display
    spec, so those are skipped here rather than raising -- they are still
    exposed to downstream physics via the model itself, just not surfaced as
    a labeled UI contribution row.
    """

    ranked = sorted(
        prediction.important_features.items(), key=lambda kv: abs(kv[1]), reverse=True
    )
    contributions: list[FeatureContribution] = []
    for key, contribution in ranked:
        spec = INDICATOR_SPECS.get(key)
        if spec is None or key not in indicators:
            continue
        contributions.append(
            FeatureContribution(
                feature=key,
                feature_label=spec.label,
                contribution=contribution,
                normal_value=spec.normal_value,
                actual_value=indicators[key],
                unit=spec.unit,
            )
        )
    return contributions
