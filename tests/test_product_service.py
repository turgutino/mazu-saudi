import pytest

from mazu_saudi.service.forecast import DemoForecastService, ForecastRequest
from mazu_saudi.service.server import dispatch_api, resolve_asset


def test_demo_forecast_contract_is_explicit_and_reproducible():
    service = DemoForecastService()
    request = ForecastRequest("arabian_peninsula", 6)
    first = service.forecast(request)
    second = service.forecast(request)
    assert first == second
    assert first["mode"] == "demo"
    assert first["scientific_evidence"] is False
    assert first["valid_time"] == "2025-09-03T00:00:00Z"
    assert first["audit"]["region_id_used_by_router"] is False
    assert len(first["cells"]) == 18 * 24
    assert pytest.approx(sum(item["weight"] for item in first["routing"]), abs=0.002) == 1


def test_forecast_request_rejects_unknown_region_and_lead():
    with pytest.raises(ValueError, match="unknown region"):
        ForecastRequest("unknown", 1).validate()
    with pytest.raises(ValueError, match="1, 3, or 6"):
        ForecastRequest("arabian_peninsula", 24).validate()


def test_api_dispatch_and_product_assets():
    payload = dispatch_api(DemoForecastService(), "/api/v1/forecast", "region=southwest_us&lead_hours=3")
    assert payload["region"]["id"] == "southwest_us"
    assert payload["lead_hours"] == 3
    page = resolve_asset("/").read_text(encoding="utf-8")
    assert "MAZU Atlas" in page
    assert "非业务预报" in page
    assert "Scientific evidence" in page


def test_dispatch_returns_safe_errors_and_blocks_path_traversal():
    with pytest.raises(ValueError, match="unknown region"):
        dispatch_api(DemoForecastService(), "/api/v1/forecast", "region=unknown&lead_hours=1")
    with pytest.raises(KeyError):
        dispatch_api(DemoForecastService(), "/api/v1/unknown")
    assert resolve_asset("/../pyproject.toml") is None
