from __future__ import annotations

import math

from app.domain.prediction import RawPrediction
from app.explanation.feature_attribution import build_feature_contributions


def test_preserves_all_model_features_and_does_not_invent_normal_values():
    raw = RawPrediction(
        model_id="test",
        model_version="1",
        model_name="test",
        probability=0.5,
        uncertainty=0.1,
        predicted_class="moderate",
        important_features={"daily_precip_total": 0.2, "neigh_ivt": -0.1, "lat": 0.01},
    )
    indicators = {"daily_precip_total": 8.0, "neigh_ivt": 120.0, "lat": 16.8}

    features = build_feature_contributions(raw, indicators)

    assert [feature.feature for feature in features] == [
        "daily_precip_total",
        "neigh_ivt",
        "lat",
    ]
    assert features[0].normal_value == 6
    assert features[1].feature_label == "邻域整层水汽输送"
    assert features[1].normal_value is None
    assert features[2].normal_value is None


def test_represents_non_finite_model_input_as_missing_json_value():
    raw = RawPrediction(
        model_id="test",
        model_version="1",
        model_name="test",
        probability=0.5,
        uncertainty=0.1,
        predicted_class="moderate",
        important_features={"sst_celsius": -0.2},
    )

    features = build_feature_contributions(raw, {"sst_celsius": math.nan})

    assert features[0].actual_value is None
