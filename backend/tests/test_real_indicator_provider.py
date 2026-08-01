"""Unit tests for RealIndicatorProvider, using a small synthetic fixture
NetCDF file (not the real ~59GB external archive) so these tests are fully
self-contained and reproducible in CI."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from app.data.real_indicator_provider import (
    INDICATORS_DIR_ENV,
    RealIndicatorProvider,
    available_for,
)
from app.domain.forecast_case import ForecastCase

# jazan region (see app/data/regions.py): lat=16.8892, lon=42.5511
LAT = np.array([17.0, 16.8, 16.6, 16.4])  # descending, like the real archive
LON = np.array([42.4, 42.6, 42.8, 43.0])
FEATURE_DATE = "20250315"  # target 2025-03-16, feature day 2025-03-15

_2D_VARS = [
    "cape", "daily_precip_total", "daily_convective_precip",
    "daily_large_scale_precip", "t2m_c", "tmax_c", "tmin_c", "heat_index_c",
    "vpd_kpa", "pwat", "ivt", "wind850_speed", "wind_shear_850_200",
    "daily_precip_anomaly", "t2m_anomaly_c", "tmax_anomaly_c",
    "wind10_speed", "dewpoint_depression_c",
]


def _build_fixture_dataset() -> xr.Dataset:
    data_vars = {}
    for i, name in enumerate(_2D_VARS):
        # distinct value per variable so we can assert the right cell is read
        grid = np.full((4, 4), float(i * 10))
        grid[0, 0] = float(i * 10 + 1)  # target cell (nearest to jazan after stride-2)
        data_vars[name] = (("latitude", "longitude"), grid)

    # sst_celsius lives on its own (time, lat, lon) grid: lat ASCENDING (the
    # reverse of the main grid's descending `latitude`) and one extra lon
    # column, matching the real archive's raw layout (see
    # real_indicator_provider.py's regridding comment). After the provider's
    # flip+truncate regrid, index [0, 0] of the main grid should read the
    # value at sst's LAST lat row (ascending -> flips to first), column 0.
    sst_lat = LAT[::-1]  # ascending
    sst_lon = np.array([42.4, 42.6, 42.8, 43.0, 43.2])  # n_lon + 1
    sst_grid = np.zeros((2, 4, 5))
    sst_grid[:, -1, 0] = 29.5  # this cell lands at main grid's [0, 0] after flip
    data_vars["sst_celsius"] = (("time", "lat", "lon"), sst_grid)

    return xr.Dataset(
        data_vars,
        coords={"latitude": LAT, "longitude": LON, "lat": sst_lat, "lon": sst_lon,
                "time": np.array([0, 1])},
    )


@pytest.fixture()
def indicators_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ds = _build_fixture_dataset()
    path = tmp_path / f"saudi_indicators_{FEATURE_DATE}.nc"
    ds.to_netcdf(path)
    monkeypatch.setenv(INDICATORS_DIR_ENV, str(tmp_path))
    return tmp_path


def _make_case(hazard: str = "extreme-heat") -> ForecastCase:
    return ForecastCase.create(
        case_id="case-test", region_id="jazan", hazard=hazard,
        lead_time_hours=24, initial_time=datetime(2025, 3, 15, tzinfo=timezone.utc),
    )


def test_available_for_false_when_archive_is_explicitly_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(INDICATORS_DIR_ENV, "")
    assert available_for(_make_case()) is False


def test_available_for_auto_discovers_local_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    monkeypatch.setattr(
        "app.data.real_indicator_provider.DEFAULT_LOCAL_INDICATORS_DIR", tmp_path
    )
    (tmp_path / f"saudi_indicators_{FEATURE_DATE}.nc").touch()
    assert available_for(_make_case()) is True


def test_available_for_false_when_file_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(INDICATORS_DIR_ENV, str(tmp_path))
    assert available_for(_make_case()) is False


def test_available_for_true_when_file_present(indicators_dir: Path):
    assert available_for(_make_case()) is True


def test_generate_reads_nearest_stride2_cell(indicators_dir: Path):
    provider = RealIndicatorProvider()
    indicators = provider.generate(_make_case())

    # cape is _2D_VARS[0] -> target cell value = 0*10 + 1 = 1.0
    assert indicators["cape"] == 1.0
    # t2m_c is _2D_VARS[4] -> target cell value = 4*10 + 1 = 41.0
    assert indicators["t2m_c"] == 41.0
    assert indicators["t2m"] == 41.0  # placeholder alias


def test_generate_does_not_invent_missing_explanation_indicators(indicators_dir: Path):
    indicators = RealIndicatorProvider().generate(_make_case())

    assert "t850" not in indicators
    assert "h500" not in indicators
    assert "rh_surface" not in indicators


def test_generate_sets_region_lat_lon_and_day_of_year(indicators_dir: Path):
    provider = RealIndicatorProvider()
    indicators = provider.generate(_make_case())

    assert indicators["lat"] == pytest.approx(16.8892)
    assert indicators["lon"] == pytest.approx(42.5511)
    assert indicators["day_of_year"] == 74.0  # 2025-03-15 is day 74


def test_generate_regrids_sst_celsius_onto_main_grid(indicators_dir: Path):
    provider = RealIndicatorProvider()
    indicators = provider.generate(_make_case())
    assert indicators["sst_celsius"] == pytest.approx(29.5)


def test_generate_computes_neighbor_means_for_heatwave_vars(indicators_dir: Path):
    provider = RealIndicatorProvider()
    indicators = provider.generate(_make_case())
    assert "neigh_cape" in indicators
    assert "neigh_pwat" in indicators


def test_generate_raises_when_archive_is_explicitly_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(INDICATORS_DIR_ENV, "")
    with pytest.raises(RuntimeError):
        RealIndicatorProvider().generate(_make_case())


def test_generate_rejects_unknown_region(indicators_dir: Path):
    case = ForecastCase.create(
        case_id="case-test", region_id="atlantis", hazard="extreme-heat",
        lead_time_hours=24, initial_time=datetime(2025, 3, 15, tzinfo=timezone.utc),
    )
    with pytest.raises(ValueError):
        RealIndicatorProvider().generate(case)
