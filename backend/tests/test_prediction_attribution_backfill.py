from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

import pytest

from app.domain.forecast_case import ForecastCase
from app.models.live_api_model import get_live_api_model
from app.repositories.prediction_store import PredictionStore
from app.repositories.sqlite_backup import create_sqlite_backup
from app.schemas.prediction import FeatureContribution, PredictionResult
from app.services.prediction_attribution_backfill import (
    backfill_prediction_attributions,
)


INDICATORS = {
    "daily_precip_total": 0.0,
    "t2m_c": 34.6583,
    "tmax_c": 37.9,
    "tmin_c": 31.9,
    "wind10_speed": 4.4396,
    "lat": 16.8892,
    "lon": 42.5511,
    "day_of_year": 214.0,
}


def _prediction(
    prediction_id: str,
    *,
    model_id: str,
    model_version: str,
    probability: float,
    raw_indicators: dict[str, float],
) -> PredictionResult:
    return PredictionResult(
        prediction_id=prediction_id,
        case_id=f"case-{prediction_id}",
        model_id=model_id,
        model_version=model_version,
        model_name="legacy",
        hazard="heavy-rain",
        hazard_label="强降雨",
        region_id="jazan",
        region_name="吉赞",
        target_time="2026-08-02T00:00:00+00:00",
        lead_time_hours=24,
        initial_time="2026-08-01T00:00:00+00:00",
        probability=probability,
        calibrated_probability=probability,
        predicted_class="low",
        uncertainty=0.1,
        features=[
            FeatureContribution(
                feature="daily_precip",
                feature_label="日降水预测",
                contribution=999.0,
                normal_value=6.0,
                actual_value=0.0,
                unit="mm",
            )
        ],
        rule_hits=[],
        mechanisms=[],
        similar_events=[],
        risk_level="green",
        risk_label="低风险",
        risk_description="test",
        input_hash="hash",
        created_at="2026-08-01T00:00:00+00:00",
        raw_indicators=raw_indicators,
        data_tier="tier2_live",
    )


def test_backfills_exact_model_and_removes_unavailable_legacy_features(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "backfill.db"))
    store = PredictionStore()
    model = get_live_api_model("heavy-rain")
    case = ForecastCase.create(
        case_id="case-current",
        region_id="jazan",
        hazard="heavy-rain",
        lead_time_hours=24,
        initial_time=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    probability = model.predict(case, INDICATORS).probability
    store.save(
        _prediction(
            "pred-current",
            model_id=model.model_id,
            model_version=model.model_version,
            probability=probability,
            raw_indicators=INDICATORS,
        )
    )
    store.save(
        _prediction(
            "pred-legacy",
            model_id="live-fusion-v1",
            model_version="v1.0.0",
            probability=0.75,
            raw_indicators={"cape": 6000.0},
        )
    )

    dry_run = backfill_prediction_attributions(store)
    assert dry_run.migrated == ["pred-current"]
    assert store.get("pred-current").attribution_method is None

    report = backfill_prediction_attributions(store, dry_run=False)
    current = store.get("pred-current")
    legacy = store.get("pred-legacy")

    assert report.migrated == ["pred-current"]
    assert report.unavailable == {
        "pred-legacy": "legacy_model_artifact_unavailable"
    }
    assert current.attribution_method == "tree_shap"
    assert len(current.features) == len(model.features)
    assert current.probability == probability
    assert current.attribution_base_value + sum(
        feature.contribution for feature in current.features
    ) == pytest.approx(current.attribution_model_output, abs=1e-5)
    assert legacy.features == []
    assert legacy.attribution_method == "unavailable:legacy_model_artifact_unavailable"
    assert legacy.probability == 0.75

    repeated = backfill_prediction_attributions(store, dry_run=False)
    assert repeated.already_current == ["pred-current"]


def test_cli_backup_uses_consistent_sqlite_copy(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    with sqlite3.connect(source) as connection:
        connection.execute("create table sample (value text)")
        connection.execute("insert into sample values ('preserved')")
        connection.commit()

    assert create_sqlite_backup(source, backup) == backup
    with sqlite3.connect(backup) as connection:
        assert connection.execute("select value from sample").fetchone() == (
            "preserved",
        )
