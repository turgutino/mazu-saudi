"""Unit tests for the SQLite-backed PredictionStore.

Verifies persistence semantics directly (independent of PredictionService):
save/get/get_by_case_id/list round-trip correctly, filtering works, and —
the main point of the SQLite migration — data survives a fresh
``PredictionStore()`` instance pointed at the same DB file (simulating a
process restart), unlike the old in-memory dict.
"""

from __future__ import annotations

from app.repositories.prediction_store import PredictionStore
from app.schemas.prediction import PredictionResult


def _make_result(
    prediction_id: str,
    case_id: str,
    region_id: str,
    hazard: str,
    data_tier: str = "tier1_real",
) -> PredictionResult:
    return PredictionResult(
        prediction_id=prediction_id,
        case_id=case_id,
        model_id="ensemble-v4",
        model_version="v4.1.0",
        model_name="多模型集成",
        hazard=hazard,
        hazard_label=hazard,
        region_id=region_id,
        region_name=region_id,
        target_time="2025-06-02T00:00:00+00:00",
        lead_time_hours=24,
        initial_time="2025-06-01T00:00:00+00:00",
        probability=0.5,
        calibrated_probability=0.5,
        predicted_class="medium",
        uncertainty=0.1,
        features=[],
        rule_hits=[],
        mechanisms=[],
        similar_events=[],
        risk_level="yellow",
        risk_label="中风险",
        risk_description="test",
        input_hash="hash",
        created_at="2025-06-01T00:00:00+00:00",
        raw_indicators={"cape": 800.0},
        data_tier=data_tier,
    )


def test_save_and_get_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "t1.db"))
    store = PredictionStore()
    result = _make_result("pred-1", "case-1", "jazan", "flash-flood")
    store.save(result)
    assert store.get("pred-1") == result
    assert store.get_by_case_id("case-1") == result
    assert store.get("does-not-exist") is None
    assert store.get("pred-1").raw_indicators == {"cape": 800.0}
    assert store.get("pred-1").data_tier == "tier1_real"


def test_list_filters_by_region_and_hazard(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "t2.db"))
    store = PredictionStore()
    store.save(_make_result("pred-1", "case-1", "jazan", "flash-flood"))
    store.save(_make_result("pred-2", "case-2", "riyadh", "extreme-heat"))

    assert {p.prediction_id for p in store.list()} == {"pred-1", "pred-2"}
    assert [p.prediction_id for p in store.list(region_id="jazan")] == ["pred-1"]
    assert [p.prediction_id for p in store.list(hazard="extreme-heat")] == ["pred-2"]
    assert store.list(region_id="jazan", hazard="extreme-heat") == []


def test_list_filters_by_data_tier(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "t5.db"))
    store = PredictionStore()
    store.save(_make_result("pred-1", "case-1", "jazan", "flash-flood", data_tier="tier1_real"))
    store.save(_make_result("pred-2", "case-2", "riyadh", "extreme-heat", data_tier="tier3_synthetic"))

    assert [p.prediction_id for p in store.list(data_tier="tier1_real")] == ["pred-1"]
    assert [p.prediction_id for p in store.list(data_tier="tier3_synthetic")] == ["pred-2"]


def test_data_survives_new_store_instance_same_db_file(tmp_path, monkeypatch):
    db_path = str(tmp_path / "t3.db")
    monkeypatch.setenv("MAZU_DB_PATH", db_path)

    store_a = PredictionStore()
    store_a.save(_make_result("pred-1", "case-1", "jazan", "flash-flood"))

    # Simulate a process restart: a brand-new PredictionStore instance
    # pointed at the same DB file must still see the earlier write.
    store_b = PredictionStore()
    assert store_b.get("pred-1") is not None
    assert store_b.get("pred-1").prediction_id == "pred-1"


def test_clear_removes_all_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "t4.db"))
    store = PredictionStore()
    store.save(_make_result("pred-1", "case-1", "jazan", "flash-flood"))
    store.clear()
    assert store.list() == []
