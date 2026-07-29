"""Stream global daily GRIB2 products into graph-ready indicator tiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np


GRAVITY = 9.80665
PIPELINE_VERSION = "1"
REQUIRED_OUTPUT_VARIABLES = (
    "ivt",
    "cape",
    "pwat",
    "daily_precip_total",
    "tmax_c",
    "wind10_speed",
    "vpd_kpa",
)
SOURCE_PATTERNS = {
    "analysis": "ART_ATM_GLB_0P10_DAY_ANAL_{day}.grib2",
    "accumulation": "ART_SINGLE_GLB_0P10_DAY_ACC_{day}.grib2",
    "maximum": "ART_SINGLE_GLB_0P10_DAY_MAX_{day}.grib2",
    "surface": "ART_SINGLE_GLB_0P10_DAY_SFC_{day}.grib2",
}


@dataclass(frozen=True)
class SaudiExclusion:
    """Conservative project-region mask, shared with the Saudi extractor."""

    lat_min: float = 16.0
    lat_max: float = 32.0
    lon_min: float = 34.0
    lon_max: float = 56.0


@dataclass(frozen=True)
class GlobalIndicatorConfig:
    year: int = 2025
    tile_degrees: float = 10.0
    ivt_levels_hpa: tuple[int, ...] = (1000, 925, 850, 700, 500, 300)
    exclusion: SaudiExclusion = SaudiExclusion()
    max_days_with_missing_sources: int = 5


@dataclass(frozen=True)
class DailySource:
    day: str
    files: dict[str, Path | None]

    @property
    def missing_products(self) -> tuple[str, ...]:
        return tuple(name for name, path in self.files.items() if path is None)


@dataclass(frozen=True)
class SourceAudit:
    year: int
    day_count: int
    complete_day_count: int
    missing_source_days: dict[str, tuple[str, ...]]


@dataclass
class TileGrid:
    tile_degrees: float
    latitudes: np.ndarray
    longitudes: np.ndarray
    tile_ids: np.ndarray
    weights: np.ndarray
    included: np.ndarray
    tile_latitudes: np.ndarray
    tile_longitudes: np.ndarray

    @classmethod
    def from_points(
        cls,
        latitudes: np.ndarray,
        longitudes: np.ndarray,
        *,
        tile_degrees: float,
        exclusion: SaudiExclusion,
    ) -> "TileGrid":
        if not 0.5 <= tile_degrees <= 30.0:
            raise ValueError("tile_degrees must be between 0.5 and 30")
        lat = np.asarray(latitudes, dtype=np.float64).reshape(-1)
        lon = normalize_longitudes(np.asarray(longitudes, dtype=np.float64).reshape(-1))
        if lat.shape != lon.shape:
            raise ValueError("GRIB latitude and longitude arrays must have the same shape")
        nlat = math.ceil(180.0 / tile_degrees)
        nlon = math.ceil(360.0 / tile_degrees)
        lat_bin = np.floor((np.clip(lat, -90.0, 90.0 - 1e-9) + 90.0) / tile_degrees)
        lon_bin = np.floor((np.clip(lon, -180.0, 180.0 - 1e-9) + 180.0) / tile_degrees)
        tile_ids = (lat_bin.astype(np.int32) * nlon + lon_bin.astype(np.int32))
        excluded = (
            (lat >= exclusion.lat_min)
            & (lat <= exclusion.lat_max)
            & (lon >= exclusion.lon_min)
            & (lon <= exclusion.lon_max)
        )
        weights = np.maximum(np.cos(np.deg2rad(lat)), 1e-8)
        tile_latitudes = -90.0 + (np.arange(nlat) + 0.5) * tile_degrees
        tile_longitudes = -180.0 + (np.arange(nlon) + 0.5) * tile_degrees
        return cls(
            tile_degrees=tile_degrees,
            latitudes=lat,
            longitudes=lon,
            tile_ids=tile_ids,
            weights=weights,
            included=~excluded,
            tile_latitudes=tile_latitudes,
            tile_longitudes=tile_longitudes,
        )

    @classmethod
    def regular(cls, config: GlobalIndicatorConfig) -> "TileGrid":
        """Create output coordinates for a day with no readable source product."""

        step = config.tile_degrees
        lat = np.arange(-90.0 + step / 2.0, 90.0, step)
        lon = np.arange(-180.0 + step / 2.0, 180.0, step)
        lat_grid, lon_grid = np.meshgrid(lat, lon, indexing="ij")
        return cls.from_points(
            lat_grid.reshape(-1),
            lon_grid.reshape(-1),
            tile_degrees=step,
            exclusion=config.exclusion,
        )

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.tile_latitudes), len(self.tile_longitudes)

    @property
    def point_count(self) -> int:
        return self.tile_ids.size

    def aggregate(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        flat = np.asarray(values, dtype=np.float64).reshape(-1)
        if flat.size != self.point_count:
            raise ValueError(
                f"GRIB field has {flat.size} cells; expected {self.point_count}"
            )
        valid = self.included & np.isfinite(flat) & (np.abs(flat) < 1e20)
        tile_count = self.shape[0] * self.shape[1]
        if not np.any(valid):
            return (
                np.full(self.shape, np.nan, dtype=np.float32),
                np.zeros(self.shape, dtype=np.int32),
            )
        ids = self.tile_ids[valid]
        weighted = self.weights[valid]
        sums = np.bincount(
            ids,
            weights=flat[valid] * weighted,
            minlength=tile_count,
        )
        weight_sums = np.bincount(ids, weights=weighted, minlength=tile_count)
        counts = np.bincount(ids, minlength=tile_count)
        means = np.full(tile_count, np.nan, dtype=np.float64)
        np.divide(sums, weight_sums, out=means, where=weight_sums > 0)
        return means.reshape(self.shape).astype(np.float32), counts.reshape(self.shape)


def normalize_longitudes(values: np.ndarray) -> np.ndarray:
    return ((values + 180.0) % 360.0) - 180.0


def iter_year_days(year: int) -> Iterable[str]:
    current = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    while current < end:
        yield current.strftime("%Y%m%d")
        current += timedelta(days=1)


def discover_daily_sources(
    data_root: Path,
    config: GlobalIndicatorConfig,
) -> list[DailySource]:
    daily_root = Path(data_root) / "2_NAFP_ART_SFC_GLB_DAY_PROD"
    sources: list[DailySource] = []
    for day in iter_year_days(config.year):
        day_root = daily_root / day
        files: dict[str, Path | None] = {}
        for product, template in SOURCE_PATTERNS.items():
            candidate = day_root / template.format(day=day)
            files[product] = candidate if candidate.is_file() else None
        sources.append(DailySource(day=day, files=files))
    return sources


def audit_sources(
    sources: Iterable[DailySource],
    config: GlobalIndicatorConfig,
) -> SourceAudit:
    records = list(sources)
    missing = {
        source.day: source.missing_products
        for source in records
        if source.missing_products
    }
    if len(missing) > config.max_days_with_missing_sources:
        raise ValueError(
            f"{len(missing)} days miss required source products; configured maximum is "
            f"{config.max_days_with_missing_sources}"
        )
    return SourceAudit(
        year=config.year,
        day_count=len(records),
        complete_day_count=len(records) - len(missing),
        missing_source_days=missing,
    )


def output_path(output_dir: Path, day: str) -> Path:
    return Path(output_dir) / f"global_excluding_saudi_indicators_{day}.nc"


def _source_manifest(source: DailySource) -> str:
    return json.dumps(
        {
            name: (
                {
                    "path": str(source_path),
                    "size": source_path.stat().st_size,
                    "mtime_ns": source_path.stat().st_mtime_ns,
                }
                if source_path is not None
                else None
            )
            for name, source_path in source.files.items()
        },
        sort_keys=True,
    )


def output_is_complete(
    path: Path,
    config: GlobalIndicatorConfig,
    source: DailySource | None = None,
) -> bool:
    if not path.is_file():
        return False
    try:
        import xarray as xr

        with xr.open_dataset(path) as dataset:
            complete = (
                dataset.attrs.get("pipeline_version") == PIPELINE_VERSION
                and float(dataset.attrs.get("tile_degrees")) == config.tile_degrees
                and dataset.attrs.get("ivt_levels_hpa")
                == ",".join(str(level) for level in config.ivt_levels_hpa)
                and dataset.attrs.get("saudi_exclusion")
                == json.dumps(asdict(config.exclusion), sort_keys=True)
                and dataset.attrs.get("saudi_cells_excluded_before_aggregation")
                == "true"
                and all(name in dataset for name in REQUIRED_OUTPUT_VARIABLES)
            )
            if source is not None:
                complete = (
                    complete
                    and dataset.attrs.get("source_file_manifest")
                    == _source_manifest(source)
                )
            return complete
    except (OSError, ValueError, KeyError):
        return False


def _require_eccodes():
    try:
        import eccodes
    except ImportError as exc:  # pragma: no cover - environment setup
        raise RuntimeError(
            "eccodes is required to stream the global GRIB2 products"
        ) from exc
    return eccodes


def _message_key(eccodes: Any, handle: Any) -> tuple[str, str, float]:
    return (
        str(eccodes.codes_get(handle, "shortName")),
        str(eccodes.codes_get(handle, "typeOfLevel")),
        float(eccodes.codes_get(handle, "level")),
    )


def _message_values(eccodes: Any, handle: Any) -> np.ndarray:
    return np.asarray(eccodes.codes_get_values(handle), dtype=np.float32)


def _message_grid(
    eccodes: Any,
    handle: Any,
    config: GlobalIndicatorConfig,
) -> TileGrid:
    return TileGrid.from_points(
        eccodes.codes_get_array(handle, "latitudes"),
        eccodes.codes_get_array(handle, "longitudes"),
        tile_degrees=config.tile_degrees,
        exclusion=config.exclusion,
    )


def _clean(values: np.ndarray, minimum: float, maximum: float) -> np.ndarray:
    result = np.asarray(values, dtype=np.float32)
    valid = np.isfinite(result) & (np.abs(result) < 1e20)
    valid &= (result >= minimum) & (result <= maximum)
    return np.where(valid, result, np.nan).astype(np.float32)


def read_single_level_fields(
    path: Path,
    selectors: dict[str, tuple[str, str, float, float, float]],
    *,
    config: GlobalIndicatorConfig,
    grid: TileGrid | None = None,
) -> tuple[dict[str, np.ndarray], TileGrid]:
    """Read selected GRIB messages while decoding only requested value arrays."""

    eccodes = _require_eccodes()
    found: dict[str, np.ndarray] = {}
    with Path(path).open("rb") as stream:
        while True:
            handle = eccodes.codes_grib_new_from_file(stream)
            if handle is None:
                break
            try:
                key = _message_key(eccodes, handle)
                for target, (short_name, level_type, level, minimum, maximum) in selectors.items():
                    if target in found or key != (short_name, level_type, float(level)):
                        continue
                    values = _clean(_message_values(eccodes, handle), minimum, maximum)
                    if grid is None:
                        grid = _message_grid(eccodes, handle, config)
                    if values.size != grid.point_count:
                        raise ValueError(f"Grid mismatch in {path.name}: {target}")
                    found[target] = values
            finally:
                eccodes.codes_release(handle)
    if grid is None:
        raise ValueError(f"No requested GRIB messages found in {path}")
    return found, grid


def trapezoid_pressure_weights(levels_hpa: tuple[int, ...]) -> dict[int, float]:
    levels = np.asarray(sorted(set(levels_hpa)), dtype=np.float64)
    if levels.size < 2 or np.any(levels <= 0):
        raise ValueError("At least two positive IVT pressure levels are required")
    weights = np.empty_like(levels)
    weights[0] = (levels[1] - levels[0]) / 2.0
    weights[-1] = (levels[-1] - levels[-2]) / 2.0
    weights[1:-1] = (levels[2:] - levels[:-2]) / 2.0
    return {
        int(level): float(weight * 100.0 / GRAVITY)
        for level, weight in zip(levels, weights)
    }


def integrate_ivt(
    humidity: dict[int, np.ndarray],
    zonal_wind: dict[int, np.ndarray],
    meridional_wind: dict[int, np.ndarray],
    levels_hpa: tuple[int, ...],
) -> np.ndarray:
    weights = trapezoid_pressure_weights(levels_hpa)
    missing = {
        variable: sorted(set(weights) - set(fields))
        for variable, fields in {
            "q": humidity,
            "u": zonal_wind,
            "v": meridional_wind,
        }.items()
        if set(weights) - set(fields)
    }
    if missing:
        raise ValueError(f"IVT source levels are incomplete: {missing}")
    first = humidity[next(iter(weights))]
    ivt_u = np.zeros_like(first, dtype=np.float64)
    ivt_v = np.zeros_like(first, dtype=np.float64)
    valid = np.ones(first.shape, dtype=bool)
    for level, weight in weights.items():
        q = humidity[level]
        u = zonal_wind[level]
        v = meridional_wind[level]
        level_valid = np.isfinite(q) & np.isfinite(u) & np.isfinite(v)
        valid &= level_valid
        ivt_u += np.where(level_valid, q * u * weight, 0.0)
        ivt_v += np.where(level_valid, q * v * weight, 0.0)
    magnitude = np.sqrt(ivt_u**2 + ivt_v**2)
    return np.where(valid, magnitude, np.nan).astype(np.float32)


def read_analysis_fields(
    path: Path,
    *,
    config: GlobalIndicatorConfig,
    grid: TileGrid | None = None,
) -> tuple[dict[str, np.ndarray], TileGrid]:
    eccodes = _require_eccodes()
    levels = set(config.ivt_levels_hpa)
    humidity: dict[int, np.ndarray] = {}
    zonal: dict[int, np.ndarray] = {}
    meridional: dict[int, np.ndarray] = {}
    fields: dict[str, np.ndarray] = {}
    with Path(path).open("rb") as stream:
        while True:
            handle = eccodes.codes_grib_new_from_file(stream)
            if handle is None:
                break
            try:
                short_name, level_type, level_value = _message_key(eccodes, handle)
                level = int(level_value)
                selected = (
                    (short_name == "cape" and level_type == "surface")
                    or (short_name == "pwat" and level_type == "atmosphereSingleLayer")
                    or (
                        short_name in {"q", "u", "v"}
                        and level_type == "isobaricInhPa"
                        and level in levels
                    )
                )
                if not selected:
                    continue
                values = _message_values(eccodes, handle)
                if grid is None:
                    grid = _message_grid(eccodes, handle, config)
                if values.size != grid.point_count:
                    raise ValueError(f"Grid mismatch in {path.name}: {short_name}")
                if short_name == "cape":
                    fields["cape"] = _clean(values, 0.0, 100_000.0)
                elif short_name == "pwat":
                    fields["pwat"] = _clean(values, 0.0, 500.0)
                elif short_name == "q":
                    humidity[level] = _clean(values, 0.0, 0.1)
                elif short_name == "u":
                    zonal[level] = _clean(values, -200.0, 200.0)
                elif short_name == "v":
                    meridional[level] = _clean(values, -200.0, 200.0)
            finally:
                eccodes.codes_release(handle)
    if grid is None:
        raise ValueError(f"No graph indicator fields found in {path}")
    fields["ivt"] = integrate_ivt(
        humidity,
        zonal,
        meridional,
        config.ivt_levels_hpa,
    )
    return fields, grid


def derive_surface_indicators(fields: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    if {"t2m", "rh2m"}.issubset(fields):
        temp_c = fields["t2m"] - 273.15
        rh = np.clip(fields["rh2m"], 0.0, 100.0)
        saturation = 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))
        result["vpd_kpa"] = np.where(
            np.isfinite(temp_c) & np.isfinite(rh),
            saturation * (1.0 - rh / 100.0),
            np.nan,
        ).astype(np.float32)
    if {"u10", "v10"}.issubset(fields):
        result["wind10_speed"] = np.sqrt(
            fields["u10"] ** 2 + fields["v10"] ** 2
        ).astype(np.float32)
    return result


def _nan_tiles(grid: TileGrid) -> np.ndarray:
    return np.full(grid.shape, np.nan, dtype=np.float32)


def _aggregate_fields(
    fields: dict[str, np.ndarray],
    grid: TileGrid,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    values: dict[str, np.ndarray] = {}
    counts: dict[str, np.ndarray] = {}
    for name in REQUIRED_OUTPUT_VARIABLES:
        if name not in fields:
            values[name] = _nan_tiles(grid)
            counts[name] = np.zeros(grid.shape, dtype=np.int32)
        else:
            values[name], counts[name] = grid.aggregate(fields[name])
    return values, counts


def read_daily_raw_indicators(
    source: DailySource,
    config: GlobalIndicatorConfig,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], TileGrid]:
    grid: TileGrid | None = None
    raw: dict[str, np.ndarray] = {}
    analysis = source.files["analysis"]
    if analysis is not None:
        analysis_fields, grid = read_analysis_fields(
            analysis,
            config=config,
            grid=grid,
        )
        raw.update(analysis_fields)
    accumulation = source.files["accumulation"]
    if accumulation is not None:
        fields, grid = read_single_level_fields(
            accumulation,
            {
                "daily_precip_total": (
                    "tp", "surface", 0.0, 0.0, 10_000.0
                )
            },
            config=config,
            grid=grid,
        )
        raw.update(fields)
    maximum = source.files["maximum"]
    if maximum is not None:
        fields, grid = read_single_level_fields(
            maximum,
            {"tmax_k": ("tmax", "heightAboveGround", 2.0, 180.0, 370.0)},
            config=config,
            grid=grid,
        )
        if "tmax_k" in fields:
            raw["tmax_c"] = fields["tmax_k"] - 273.15
    surface = source.files["surface"]
    if surface is not None:
        fields, grid = read_single_level_fields(
            surface,
            {
                "t2m": ("2t", "heightAboveGround", 2.0, 180.0, 370.0),
                "rh2m": ("2r", "heightAboveGround", 2.0, 0.0, 100.0),
                "u10": ("10u", "heightAboveGround", 10.0, -200.0, 200.0),
                "v10": ("10v", "heightAboveGround", 10.0, -200.0, 200.0),
            },
            config=config,
            grid=grid,
        )
        raw.update(derive_surface_indicators(fields))
    if grid is None:
        grid = TileGrid.regular(config)
    values, counts = _aggregate_fields(raw, grid)
    return values, counts, grid


def write_daily_indicators(
    source: DailySource,
    output_dir: Path,
    config: GlobalIndicatorConfig,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    path = output_path(output_dir, source.day)
    if not overwrite and output_is_complete(path, config, source):
        return {
            "day": source.day,
            "status": "skipped_existing",
            "output": str(path),
            "missing_products": list(source.missing_products),
        }
    values, counts, grid = read_daily_raw_indicators(source, config)
    import xarray as xr

    coordinates = {
        "latitude": grid.tile_latitudes.astype(np.float32),
        "longitude": grid.tile_longitudes.astype(np.float32),
    }
    variables: dict[str, Any] = {}
    units = {
        "ivt": "kg m-1 s-1",
        "cape": "J kg-1",
        "pwat": "kg m-2",
        "daily_precip_total": "mm",
        "tmax_c": "degC",
        "wind10_speed": "m s-1",
        "vpd_kpa": "kPa",
    }
    for name, array in values.items():
        variables[name] = (
            ("latitude", "longitude"),
            array,
            {"units": units[name], "aggregation": "area-weighted tile mean"},
        )
        variables[f"{name}_valid_cell_count"] = (
            ("latitude", "longitude"),
            counts[name],
            {"units": "cells"},
        )
    dataset = xr.Dataset(
        variables,
        coords=coordinates,
        attrs={
            "pipeline_version": PIPELINE_VERSION,
            "period": source.day,
            "source_product": "2_NAFP_ART_SFC_GLB_DAY_PROD",
            "source_files": json.dumps(
                {
                    name: str(path) if path is not None else None
                    for name, path in source.files.items()
                },
                sort_keys=True,
            ),
            "source_file_manifest": _source_manifest(source),
            "missing_source_products": ",".join(source.missing_products),
            "tile_degrees": config.tile_degrees,
            "saudi_exclusion": json.dumps(asdict(config.exclusion), sort_keys=True),
            "saudi_cells_excluded_before_aggregation": "true",
            "ivt_levels_hpa": ",".join(str(level) for level in config.ivt_levels_hpa),
            "ivt_method": "pressure-level trapezoidal integration before tile aggregation",
        },
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    encoding = {
        name: {"zlib": True, "complevel": 4}
        for name in dataset.data_vars
    }
    dataset.to_netcdf(temporary, encoding=encoding)
    temporary.replace(path)
    return {
        "day": source.day,
        "status": "computed",
        "output": str(path),
        "missing_products": list(source.missing_products),
        "indicator_count": len(REQUIRED_OUTPUT_VARIABLES),
    }


def append_manifest(path: Path, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def compute_global_indicator_year(
    sources: Iterable[DailySource],
    output_dir: Path,
    config: GlobalIndicatorConfig,
    *,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
    overwrite: bool = False,
    fail_fast: bool = False,
    manifest: Path | None = None,
) -> list[dict[str, Any]]:
    selected = [
        source
        for source in sources
        if (start is None or source.day >= start)
        and (end is None or source.day <= end)
    ]
    if limit is not None:
        selected = selected[:limit]
    results: list[dict[str, Any]] = []
    for index, source in enumerate(selected, start=1):
        try:
            payload = write_daily_indicators(
                source,
                output_dir,
                config,
                overwrite=overwrite,
            )
        except Exception as exc:
            payload = {
                "day": source.day,
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            if manifest is not None:
                append_manifest(manifest, payload)
            results.append(payload)
            print(
                f"[{index}/{len(selected)}] error {source.day}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            if fail_fast:
                raise
            continue
        if manifest is not None:
            append_manifest(manifest, payload)
        results.append(payload)
        print(
            f"[{index}/{len(selected)}] {payload['status']} {source.day}",
            flush=True,
        )
    return results
