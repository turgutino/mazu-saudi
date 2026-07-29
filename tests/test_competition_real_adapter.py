import pytest

from mazu_saudi.competition.adapters import HistoricalToolAdapter
from mazu_saudi.competition.settings import AppSettings


@pytest.fixture(scope="module")
def real_adapter():
    settings = AppSettings()
    if not settings.preflight()["ready_for_inference"]:
        pytest.skip("Local historical data/model bundle is unavailable")
    return HistoricalToolAdapter(settings)


def test_real_city_forecast_matches_frozen_verified_result(real_adapter):
    result = real_adapter.forecast("Mecca", "2025-08-04", "heatwave")
    assert result["features_from_date"] == "2025-08-03"
    assert result["probability"] == pytest.approx(0.8985, abs=1e-4)
    assert result["reflexive_check"]["consistency"] == "model_higher_than_detection"
    assert result["uncertainty"]["n_members"] == 5


def test_real_probability_field_is_model_derived_and_cached(real_adapter):
    first = real_adapter.field("2025-08-04", "heatwave", "probability")
    second = real_adapter.field("2025-08-04", "heatwave", "probability")
    assert (first["rows"], first["columns"]) == (80, 110)
    assert len(first["values"]) == 80 * 110
    assert first["maximum"] == pytest.approx(0.99838, abs=1e-5)
    assert first["cache"] == "miss"
    assert second["cache"] == "hit"


def test_real_cap_never_claims_actual_status(real_adapter):
    cap = real_adapter.cap("Mecca", "2025-08-04", "heatwave")
    assert cap["alert_warranted"] is True
    assert "<status>Exercise</status>" in cap["cap_xml"]
    assert "<status>Actual</status>" not in cap["cap_xml"]
