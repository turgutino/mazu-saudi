"""RealIndicatorProvider: reads archived NetCDF indicator fields (Tier 1).

Ports the exact feature-extraction methodology of
reference_code/mazu-saudi-warning/agent/tools.py::forecast_tool onto the
mazu-saudi backend's ForecastCase: forecasts for ``case.target_time``'s date
are built from the PREVIOUS day's indicators (t-1 -> t), read from
``saudi_indicators_YYYYMMDD.nc`` files, at the stride-2-subsampled grid cell
nearest the region's lat/lon. Only available when:

  1. ``MAZU_INDICATORS_DIR`` points at a directory containing these files, or
     the project's known local archive mount exists. An explicitly empty env
     value disables archive discovery for tests or live-only deployments.
  2. the feature-day file actually exists on disk (2025 historical archive
     only; see this repo's data source note).

``available_for(case)`` lets PredictionService cheaply check both before
committing to this tier, so it can fall back to Tier 2/3 without raising.
"""

from __future__ import annotations

import datetime as dt
import calendar
import os
from pathlib import Path

import numpy as np

from app.data.regions import get_region
from app.domain.forecast_case import ForecastCase

INDICATORS_DIR_ENV = "MAZU_INDICATORS_DIR"
DEFAULT_LOCAL_INDICATORS_DIR = Path("/Volumes/E/气象数据/saudi_region_output/indicators")
STRIDE = 2

# neighbor-mean features required only by the heatwave model (see
# model/06_baseline_with_neighbors.py::NEIGHBOR_VARS).
NEIGHBOR_VARS = [
    "cape", "daily_precip_total", "ivt", "vpd_kpa",
    "wind_shear_850_200", "pwat", "daily_convective_precip",
]

# maps the narrow placeholder indicator keys (consumed by RiskPolicy /
# feature_attribution / mechanism_explanation) onto real NetCDF variable
# names, so real data transparently backs the existing UI-facing contract.
_PLACEHOLDER_ALIASES: dict[str, str] = {
    "cape": "cape",
    "pw": "pwat",
    "daily_precip": "daily_precip_total",
    "t2m": "t2m_c",
    "wind_10m": "wind10_speed",
}


def _indicators_root() -> Path | None:
    if INDICATORS_DIR_ENV in os.environ:
        value = os.environ[INDICATORS_DIR_ENV]
        return Path(value) if value else None
    if DEFAULT_LOCAL_INDICATORS_DIR.is_dir():
        return DEFAULT_LOCAL_INDICATORS_DIR
    return None


def _file_for_date(root: Path, date: dt.date) -> Path:
    return root / f"saudi_indicators_{date.strftime('%Y%m%d')}.nc"


def _feature_date(case: ForecastCase) -> dt.date:
    """The archived day whose indicators feed a forecast for target_time's
    date: target_date - 1 day (genuine t-1 -> t forecasting)."""
    return case.target_time.date() - dt.timedelta(days=1)


def _day_of_year_365(date: dt.date) -> int:
    day = date.timetuple().tm_yday
    if calendar.isleap(date.year):
        if date.month == 2 and date.day == 29:
            return 59
        if day > 59:
            return day - 1
    return day


def available_for(case: ForecastCase) -> bool:
    """True iff a real archived NetCDF file exists for this case's feature day."""
    root = _indicators_root()
    if root is None or get_region(case.region_id) is None:
        return False
    return _file_for_date(root, _feature_date(case)).exists()


def _neighbor_mean(arr: np.ndarray) -> np.ndarray:
    n_lat, n_lon = arr.shape
    total = np.zeros_like(arr, dtype="float64")
    count = np.zeros_like(arr, dtype="float64")
    valid = np.isfinite(arr)
    filled = np.where(valid, arr, 0.0)
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ys, ye = max(0, dy), n_lat + min(0, dy)
        xs, xe = max(0, dx), n_lon + min(0, dx)
        ys2, ye2 = max(0, -dy), n_lat + min(0, -dy)
        xs2, xe2 = max(0, -dx), n_lon + min(0, -dx)
        shifted_val = np.zeros_like(arr, dtype="float64")
        shifted_valid = np.zeros_like(arr, dtype=bool)
        shifted_val[ys2:ye2, xs2:xe2] = filled[ys:ye, xs:xe]
        shifted_valid[ys2:ye2, xs2:xe2] = valid[ys:ye, xs:xe]
        total += np.where(shifted_valid, shifted_val, 0.0)
        count += shifted_valid.astype("float64")
    return total / np.maximum(count, 1)


class RealIndicatorProvider:
    """Reads real archived NetCDF indicators for a ForecastCase (Tier 1)."""

    def generate(self, case: ForecastCase) -> dict[str, float]:
        import xarray as xr  # local import: optional heavy dependency

        region = get_region(case.region_id)
        if region is None:
            raise ValueError(f"Unknown regionId: {case.region_id}")
        root = _indicators_root()
        if root is None:
            raise RuntimeError(f"{INDICATORS_DIR_ENV} is not configured")

        feature_date = _feature_date(case)
        path = _file_for_date(root, feature_date)
        if not path.exists():
            raise FileNotFoundError(f"No archived indicators for {feature_date}: {path}")

        raw: dict[str, float] = {}
        with xr.open_dataset(path) as ds:
            lat_full = ds["latitude"].values
            lon_full = ds["longitude"].values
            yi_s = np.arange(0, len(lat_full), STRIDE)
            xi_s = np.arange(0, len(lon_full), STRIDE)
            lat_s, lon_s = lat_full[yi_s], lon_full[xi_s]
            yi = int(np.argmin(np.abs(lat_s - region.lat)))
            xi = int(np.argmin(np.abs(lon_s - region.lon)))

            n_lat, n_lon = len(lat_full), len(lon_full)
            for name, array in ds.data_vars.items():
                if tuple(array.dims) != ("latitude", "longitude"):
                    continue
                sub = array.values[yi_s][:, xi_s]
                value = float(sub[yi, xi])
                if np.isfinite(value):
                    raw[name] = value

            # sst_celsius lives on its own (time, lat, lon) grid: shape
            # (n_time, n_lat, n_lon+1), lat ASCENDING (vs. the main grid's
            # descending latitude) and one extra longitude column. Regrid it
            # onto the main (latitude, longitude) index space exactly as
            # pipeline/01_build_dataset.py does -- time-mean, flip the lat
            # axis, drop the trailing lon column -- so the resulting array
            # aligns index-for-index with the main grid and can be indexed
            # with the SAME stride-2 (yi_s, xi_s) / nearest-cell (yi, xi)
            # already computed above.
            if "sst_celsius" in ds:
                sst = ds["sst_celsius"]
                if "time" in sst.dims:
                    sst = sst.mean(dim="time", skipna=True)
                sst_regridded = sst.values[::-1, :n_lon]
                if sst_regridded.shape == (n_lat, n_lon):
                    sub = sst_regridded[yi_s][:, xi_s]
                    value = float(sub[yi, xi])
                    # HistGradientBoostingClassifier natively supports NaN
                    # (learns a missing-value split direction at train time),
                    # so pass it through rather than dropping the feature --
                    # dropping it entirely would trip the "missing required
                    # feature" check in JoblibForecastModel.
                    raw["sst_celsius"] = value

            if all(v in raw for v in NEIGHBOR_VARS):
                for name in NEIGHBOR_VARS:
                    full = ds[name].values
                    neighbor_sub = _neighbor_mean(full)[yi_s][:, xi_s]
                    value = float(neighbor_sub[yi, xi])
                    if np.isfinite(value):
                        raw[f"neigh_{name}"] = value

        raw["lat"] = region.lat
        raw["lon"] = region.lon
        raw["day_of_year"] = float(_day_of_year_365(feature_date))

        overrides = {
            placeholder_key: raw[real_key]
            for placeholder_key, real_key in _PLACEHOLDER_ALIASES.items()
            if real_key in raw
        }
        # Keep only archive-backed values and aliases of those same values.
        # Missing explanation indicators must remain missing so mechanism
        # coverage is reduced instead of silently receiving synthetic inputs.
        raw.update(overrides)
        return raw


real_indicator_provider = RealIndicatorProvider()
