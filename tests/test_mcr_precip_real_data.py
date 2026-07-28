from pathlib import Path

import numpy as np
import pytest

from mazu_saudi.mcr_precip.real_data import (
    FEATURE_VARS,
    SplitConfig,
    fit_channel_stats,
    prepare_proxy_data,
    split_valid_dates,
)


xr = pytest.importorskip("xarray")


def _write_dataset(path: Path, terrain_path: Path):
    time = np.arange("2025-01-01", "2025-01-09", dtype="datetime64[D]")
    lat = np.array([2.0, 1.0, 0.0], dtype=np.float32)
    lon = np.array([10.0, 11.0, 12.0, 13.0], dtype=np.float32)
    shape = (len(time), len(lat), len(lon))
    variables = {}
    for index, name in enumerate(FEATURE_VARS):
        values = np.full(shape, index + 1, dtype=np.float32)
        values[:, 0, 0] += np.arange(len(time), dtype=np.float32)
        variables[name] = (("time", "latitude", "longitude"), values)
    label = np.zeros(shape, dtype=np.float32)
    label[1, 1, 2] = 2
    label[6, 0, 0] = 3
    variables["flash_flood_risk"] = (("time", "latitude", "longitude"), label)
    dataset = xr.Dataset(
        variables,
        coords={"time": time, "latitude": lat, "longitude": lon},
    )
    dataset.to_netcdf(path)
    xr.Dataset(
        {"orography": (("latitude", "longitude"), np.arange(12).reshape(3, 4))},
        coords={"latitude": lat, "longitude": lon},
    ).to_netcdf(terrain_path)


def test_split_uses_forecast_valid_date_and_has_no_overlap():
    dates = [f"2025-01-{day:02d}" for day in range(2, 9)]
    split = split_valid_dates(
        dates,
        SplitConfig(
            train_end="2025-01-04",
            validation_start="2025-01-05",
            validation_end="2025-01-06",
        ),
    )
    assert split.train.tolist() == [0, 1, 2]
    assert split.validation.tolist() == [3, 4]
    assert split.test.tolist() == [5, 6]


def test_channel_statistics_ignore_future_extremes():
    raw = np.ones((4, 2, 2, 2), dtype=np.float32)
    raw[2:] = 1000
    stats = fit_channel_stats(raw, np.array([0, 1]))
    assert np.allclose(stats.mean, 1)
    assert np.allclose(stats.median, 1)


def test_adapter_builds_t_plus_one_24_hour_batch(tmp_path):
    dataset_path = tmp_path / "dataset.nc"
    terrain_path = tmp_path / "terrain.nc"
    _write_dataset(dataset_path, terrain_path)
    data = prepare_proxy_data(
        dataset_path,
        terrain_path,
        stride=1,
        split_config=SplitConfig(
            train_end="2025-01-04",
            validation_start="2025-01-05",
            validation_end="2025-01-06",
        ),
    )
    assert data.dynamic.shape == (7, 1, len(FEATURE_VARS) + 2, 3, 4)
    assert data.valid_dates[0] == "2025-01-02"
    assert data.input_dates[0] == "2025-01-01"
    assert data.occurrence[0, 0, 1, 2].item() == 1
    assert data.lead_hours.unique().tolist() == [24]
    assert data.terrain_available
    data.batch([0, 1]).validate(8, 3)
