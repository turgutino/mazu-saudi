"""Build a small statistical graph from one year of daily indicator cubes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable
from uuid import uuid4
import warnings

import numpy as np

from .store import KnowledgeGraphStore, PROV_WAS_GENERATED_BY
from .relation_policy import RELATION_POLICY_VERSION, assess_relation


MAZU = "urn:mazu-saudi:ontology:"
CONCEPT = "urn:mazu-saudi:concept:"
PROV_USED = "http://www.w3.org/ns/prov#used"
PROV_WAS_DERIVED_FROM = "http://www.w3.org/ns/prov#wasDerivedFrom"

AUXILIARY_INDICATORS = (
    "satellite_precip_total",
    "satellite_precip_coverage",
    "sst_c",
    "monthly_precip_total",
    "monthly_tmax_c",
)
DYNAMIC_INDICATORS = frozenset({"ivt", "cape", "pwat"})
DATA_SOURCE_IRIS = {
    "ds1": f"{CONCEPT}NAFPMonthlyAtmosphericProduct",
    "ds2": f"{CONCEPT}NAFPDailyAtmosphericProduct",
    "ds4": f"{CONCEPT}CODASSeaSurfaceTemperatureProduct",
    "ds10": f"{CONCEPT}FYMERGSatellitePrecipitationProduct",
}
INDICATOR_SOURCE_KEYS = {
    "ivt": ("ds2",),
    "cape": ("ds2",),
    "pwat": ("ds2",),
    "daily_precip_total": ("ds2",),
    "tmax_c": ("ds2",),
    "wind10_speed": ("ds2",),
    "vpd_kpa": ("ds2",),
    "satellite_precip_total": ("ds10",),
    "sst_c": ("ds4",),
    "monthly_precip_total": ("ds1",),
    "monthly_tmax_c": ("ds1",),
}


@dataclass(frozen=True)
class IndicatorStateSpec:
    """Map one or more existing indicators to an ontology state concept."""

    name: str
    label_zh: str
    ontology_class_iri: str
    concept_iri: str
    indicators: tuple[str, ...]
    indicator_iris: tuple[str, ...]
    quantile: float
    required_for_formal_graph: bool = True
    phenomenon_family: str = "unspecified"


DEFAULT_STATE_SPECS = (
    IndicatorStateSpec(
        "high_ivt",
        "高水汽输送状态",
        f"{MAZU}IndicatorState",
        f"{CONCEPT}HighIVTState",
        ("ivt",),
        (f"{CONCEPT}IntegratedVaporTransport",),
        0.90,
        phenomenon_family="moisture_transport",
    ),
    IndicatorStateSpec(
        "high_cape",
        "高对流不稳定状态",
        f"{MAZU}IndicatorState",
        f"{CONCEPT}HighCAPEState",
        ("cape",),
        (f"{CONCEPT}CAPE",),
        0.90,
        phenomenon_family="convection_instability",
    ),
    IndicatorStateSpec(
        "moist_atmosphere",
        "高水汽含量状态",
        f"{MAZU}IndicatorState",
        f"{CONCEPT}MoistAtmosphereState",
        ("pwat",),
        (f"{CONCEPT}PrecipitableWater",),
        0.90,
        phenomenon_family="atmospheric_moisture",
    ),
    IndicatorStateSpec(
        "extreme_rainfall",
        "极端降水状态",
        f"{MAZU}ExtremeWeatherState",
        f"{CONCEPT}ExtremeRainfallState",
        ("daily_precip_total",),
        (f"{CONCEPT}DailyPrecipitation",),
        0.95,
        phenomenon_family="precipitation",
    ),
    IndicatorStateSpec(
        "high_satellite_rainfall",
        "卫星高降水状态",
        f"{MAZU}IndicatorState",
        f"{CONCEPT}HighSatelliteRainfallState",
        ("satellite_precip_total",),
        (f"{CONCEPT}SatelliteDailyPrecipitation",),
        0.95,
        required_for_formal_graph=False,
        phenomenon_family="precipitation",
    ),
    IndicatorStateSpec(
        "warm_sea_surface",
        "暖海温状态",
        f"{MAZU}IndicatorState",
        f"{CONCEPT}WarmSeaSurfaceState",
        ("sst_c",),
        (f"{CONCEPT}SeaSurfaceTemperature",),
        0.90,
        phenomenon_family="sea_surface_temperature",
    ),
    IndicatorStateSpec(
        "extreme_heat",
        "极端高温状态",
        f"{MAZU}ExtremeWeatherState",
        f"{CONCEPT}ExtremeHeatState",
        ("tmax_c",),
        (f"{CONCEPT}MaximumAirTemperature",),
        0.95,
        phenomenon_family="air_temperature",
    ),
    IndicatorStateSpec(
        "strong_dry_wind",
        "强风干燥状态",
        f"{MAZU}IndicatorState",
        f"{CONCEPT}StrongDryWindState",
        ("wind10_speed", "vpd_kpa"),
        (f"{CONCEPT}TenMetreWindSpeed", f"{CONCEPT}VaporPressureDeficit"),
        0.90,
        phenomenon_family="dry_wind",
    ),
)


@dataclass(frozen=True)
class BuildConfig:
    year: int = 2025
    file_glob: str = "*.nc"
    scope_label: str = "global-2025"
    tile_degrees: float = 10.0
    max_lag_days: int = 3
    min_support_episodes: int = 8
    min_lift: float = 1.15
    min_candidate_support_rate: float = 0.25
    max_assertions: int = 160
    evidence_episode_limit: int = 12
    min_indicator_file_coverage: float = 0.50
    min_indicator_season_coverage: float = 0.75
    allow_degraded_coverage: bool = False
    require_complete_year: bool = True


@dataclass(frozen=True)
class BuildResult:
    build_id: str
    database_file: str
    input_file_count: int
    spatial_tile_count: int
    node_count: int
    edge_count: int
    assertion_count: int
    prediction_candidate_count: int
    diagnostic_assertion_count: int
    episode_count: int
    threshold_count: int
    start_date: str
    end_date: str


@dataclass
class AggregatedIndicators:
    dates: list[date]
    spatial_keys: list[str]
    tile_latitudes: np.ndarray
    tile_longitudes: np.ndarray
    values: dict[str, np.ndarray]
    file_coverage: dict[str, float]
    seasonal_file_coverage: dict[str, dict[str, float]]
    source_quality_counts: dict[str, int]


@dataclass(frozen=True)
class Episode:
    state_index: int
    tile_index: int
    season: str
    start_index: int
    end_index: int


@dataclass(frozen=True)
class Association:
    source_state_index: int
    target_state_index: int
    season: str
    lag_days: int
    opportunity_count: int
    source_occurrence_count: int
    target_occurrence_count: int
    joint_occurrence_count: int
    support_episode_indices: tuple[int, ...]
    counterexample_episode_indices: tuple[int, ...]
    baseline_rate: float
    conditional_rate: float
    lift: float


def _season(day: date) -> str:
    if day.month in (12, 1, 2):
        return "DJF"
    if day.month in (3, 4, 5):
        return "MAM"
    if day.month in (6, 7, 8):
        return "JJA"
    return "SON"


def _date_from_path(path: Path) -> date:
    matches = re.findall(r"(?<!\d)(20\d{6})(?!\d)", path.stem)
    if not matches:
        raise ValueError(f"Cannot find YYYYMMDD date in indicator filename: {path.name}")
    return datetime.strptime(matches[-1], "%Y%m%d").date()


def discover_indicator_files(input_dir: Path, config: BuildConfig) -> list[tuple[date, Path]]:
    input_dir = Path(input_dir)
    dated: dict[date, Path] = {}
    for path in sorted(input_dir.glob(config.file_glob)):
        if not path.is_file() or path.name.startswith("._"):
            continue
        day = _date_from_path(path)
        if day.year != config.year:
            continue
        if day in dated:
            raise ValueError(f"Duplicate indicator date {day}: {dated[day]} and {path}")
        dated[day] = path
    files = sorted(dated.items())
    if not files:
        raise ValueError(f"No {config.year} indicator files matched {input_dir / config.file_glob}")
    expected = 366 if _is_leap_year(config.year) else 365
    if config.require_complete_year and len(files) != expected:
        raise ValueError(
            f"Expected a complete {config.year} year ({expected} files), found {len(files)}; "
            "use --allow-incomplete-year only for a deliberate partial build"
        )
    return files


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _manifest_sha256(input_dir: Path, files: Iterable[tuple[date, Path]]) -> str:
    manifest = [
        {
            "date": day.isoformat(),
            "path": str(path.relative_to(input_dir)),
            "size": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
        }
        for day, path in files
    ]
    return sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _tile_layout(tile_degrees: float) -> tuple[int, int]:
    if not (0.5 <= tile_degrees <= 30.0):
        raise ValueError("tile_degrees must be between 0.5 and 30")
    nlat = math.ceil(180.0 / tile_degrees)
    nlon = math.ceil(360.0 / tile_degrees)
    return nlat, nlon


def _coordinate_name(dataset: Any, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in dataset.coords:
            return name
    raise ValueError(f"Indicator dataset misses coordinate {candidates}")


def aggregate_daily_indicators(
    files: list[tuple[date, Path]],
    state_specs: tuple[IndicatorStateSpec, ...],
    *,
    tile_degrees: float,
) -> AggregatedIndicators:
    """Stream daily grids and aggregate existing indicators to coarse global tiles."""

    try:
        import xarray as xr
    except ImportError as exc:  # pragma: no cover - environment error
        raise RuntimeError("xarray is required to read indicator NetCDF files") from exc

    required_indicator_names = tuple(
        dict.fromkeys(indicator for spec in state_specs for indicator in spec.indicators)
    )
    indicator_names = tuple(
        dict.fromkeys((*required_indicator_names, *AUXILIARY_INDICATORS))
    )
    nlat, nlon = _tile_layout(tile_degrees)
    tile_count = nlat * nlon
    values = {
        name: np.full((len(files), tile_count), np.nan, dtype=np.float32)
        for name in indicator_names
    }
    active = np.zeros(tile_count, dtype=bool)
    indicator_file_counts = {name: 0 for name in indicator_names}
    source_quality_counts: dict[str, int] = {}

    for day_index, (_, path) in enumerate(files):
        with xr.open_dataset(path) as dataset:
            lat_name = _coordinate_name(dataset, ("latitude", "lat"))
            lon_name = _coordinate_name(dataset, ("longitude", "lon"))
            latitudes = np.asarray(dataset[lat_name].values, dtype=np.float64)
            longitudes = np.asarray(dataset[lon_name].values, dtype=np.float64)
            if latitudes.ndim != 1 or longitudes.ndim != 1:
                raise ValueError(f"{path.name}: only one-dimensional lat/lon coordinates are supported")
            lon_normalized = (longitudes + 180.0) % 360.0 - 180.0
            lat_grid, lon_grid = np.meshgrid(latitudes, lon_normalized, indexing="ij")
            lat_bin = np.floor((lat_grid + 90.0) / tile_degrees).astype(np.int64)
            lon_bin = np.floor((lon_grid + 180.0) / tile_degrees).astype(np.int64)
            lat_bin = np.clip(lat_bin, 0, nlat - 1)
            lon_bin = np.clip(lon_bin, 0, nlon - 1)
            tile_ids = (lat_bin * nlon + lon_bin).ravel()
            available_indicators: set[str] = set()

            for indicator in indicator_names:
                if indicator not in dataset:
                    continue
                array = dataset[indicator]
                extra_dims = set(array.dims) - {lat_name, lon_name}
                if extra_dims:
                    raise ValueError(
                        f"{path.name}: indicator '{indicator}' has unsupported dimensions "
                        f"{array.dims}; expected only {lat_name}/{lon_name}"
                    )
                raw = np.asarray(array.transpose(lat_name, lon_name).values, dtype=np.float64).ravel()
                valid = np.isfinite(raw) & (np.abs(raw) < 1.0e20)
                if np.any(valid):
                    indicator_file_counts[indicator] += 1
                    available_indicators.add(indicator)
                sums = np.bincount(
                    tile_ids[valid],
                    weights=raw[valid],
                    minlength=tile_count,
                )
                counts = np.bincount(tile_ids[valid], minlength=tile_count)
                aggregated = np.divide(
                    sums,
                    counts,
                    out=np.full(tile_count, np.nan, dtype=np.float64),
                    where=counts > 0,
                )
                values[indicator][day_index] = aggregated.astype(np.float32)
                active |= counts > 0
            quality_attr = dataset.attrs.get("analysis_source_quality")
            if quality_attr is None:
                quality = (
                    "complete_unrecorded_v3"
                    if {"ivt", "cape", "pwat"}.issubset(
                        available_indicators
                    )
                    else "degraded_unrecorded_v3"
                )
            else:
                quality = str(quality_attr)
            source_quality_counts[quality] = (
                source_quality_counts.get(quality, 0) + 1
            )

    active_ids = np.flatnonzero(active)
    formally_required_indicator_names = {
        indicator
        for spec in state_specs
        if spec.required_for_formal_graph
        for indicator in spec.indicators
    }
    absent = [
        indicator
        for indicator in formally_required_indicator_names
        if indicator_file_counts[indicator] == 0
    ]
    if absent:
        raise ValueError(f"Required indicators are absent from every input file: {absent}")
    spatial_keys: list[str] = []
    tile_latitudes: list[float] = []
    tile_longitudes: list[float] = []
    for tile_id in active_ids:
        lat_index, lon_index = divmod(int(tile_id), nlon)
        lat_min = -90.0 + lat_index * tile_degrees
        lon_min = -180.0 + lon_index * tile_degrees
        spatial_keys.append(f"tile:{lat_min:.3f}:{lon_min:.3f}:{tile_degrees:.3f}")
        tile_latitudes.append(min(90.0, lat_min + tile_degrees / 2.0))
        tile_longitudes.append(min(180.0, lon_min + tile_degrees / 2.0))
    seasons = np.asarray([_season(day) for day, _ in files])
    seasonal_file_coverage: dict[str, dict[str, float]] = {}
    for name, array in values.items():
        available_by_day = np.any(np.isfinite(array), axis=1)
        seasonal_file_coverage[name] = {}
        for season in ("DJF", "MAM", "JJA", "SON"):
            season_mask = seasons == season
            if not np.any(season_mask):
                continue
            seasonal_file_coverage[name][season] = float(
                np.mean(available_by_day[season_mask])
            )
    return AggregatedIndicators(
        dates=[day for day, _ in files],
        spatial_keys=spatial_keys,
        tile_latitudes=np.asarray(tile_latitudes),
        tile_longitudes=np.asarray(tile_longitudes),
        values={name: array[:, active_ids] for name, array in values.items()},
        file_coverage={
            name: count / len(files)
            for name, count in indicator_file_counts.items()
        },
        seasonal_file_coverage=seasonal_file_coverage,
        source_quality_counts=source_quality_counts,
    )


def _derive_states(
    aggregated: AggregatedIndicators,
    state_specs: tuple[IndicatorStateSpec, ...],
) -> tuple[
    list[np.ndarray],
    list[np.ndarray],
    dict[tuple[int, str, int, str], tuple[float, int]],
]:
    seasons = np.asarray([_season(day) for day in aggregated.dates])
    state_flags: list[np.ndarray] = []
    availability: list[np.ndarray] = []
    thresholds: dict[tuple[int, str, int, str], tuple[float, int]] = {}

    for state_index, spec in enumerate(state_specs):
        state_available = np.ones(
            (len(aggregated.dates), len(aggregated.spatial_keys)),
            dtype=bool,
        )
        for indicator in spec.indicators:
            state_available &= np.isfinite(aggregated.values[indicator])
        flags = np.zeros_like(state_available)
        for season in ("DJF", "MAM", "JJA", "SON"):
            day_mask = seasons == season
            if not day_mask.any():
                for indicator in spec.indicators:
                    for tile_index in range(len(aggregated.spatial_keys)):
                        thresholds[(state_index, season, tile_index, indicator)] = (
                            math.nan,
                            0,
                        )
                continue
            for indicator in spec.indicators:
                season_values = aggregated.values[indicator][day_mask]
                with warnings.catch_warnings(), np.errstate(all="ignore"):
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    threshold_values = np.nanquantile(
                        season_values,
                        spec.quantile,
                        axis=0,
                    )
                sample_counts = np.isfinite(season_values).sum(axis=0)
                for tile_index, (threshold, count) in enumerate(
                    zip(threshold_values, sample_counts, strict=True)
                ):
                    thresholds[(state_index, season, tile_index, indicator)] = (
                        float(threshold) if np.isfinite(threshold) else math.nan,
                        int(count),
                    )
            compound = np.ones(
                (int(day_mask.sum()), len(aggregated.spatial_keys)),
                dtype=bool,
            )
            for indicator in spec.indicators:
                season_values = aggregated.values[indicator][day_mask]
                threshold_values = np.asarray(
                    [
                        thresholds[(state_index, season, tile_index, indicator)][0]
                        for tile_index in range(len(aggregated.spatial_keys))
                    ]
                )
                with warnings.catch_warnings(), np.errstate(all="ignore"):
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    variable = (
                        np.nanmax(season_values, axis=0)
                        > np.nanmin(season_values, axis=0)
                    )
                compound &= season_values >= threshold_values
                compound &= variable
            flags[day_mask] = compound & state_available[day_mask]
        state_flags.append(flags)
        availability.append(state_available)
    return state_flags, availability, thresholds


def _extract_episodes(
    dates: list[date],
    state_flags: list[np.ndarray],
) -> tuple[list[Episode], dict[tuple[int, str], list[int]]]:
    episodes: list[Episode] = []
    by_state_season: dict[tuple[int, str], list[int]] = {}
    for state_index, flags in enumerate(state_flags):
        for tile_index in range(flags.shape[1]):
            start: int | None = None
            for day_index in range(flags.shape[0] + 1):
                current = day_index < flags.shape[0] and bool(flags[day_index, tile_index])
                consecutive = (
                    start is not None
                    and day_index < flags.shape[0]
                    and (dates[day_index] - dates[day_index - 1]).days == 1
                    and _season(dates[day_index]) == _season(dates[start])
                )
                if current and start is None:
                    start = day_index
                elif current and consecutive:
                    continue
                elif start is not None:
                    episode = Episode(
                        state_index=state_index,
                        tile_index=tile_index,
                        season=_season(dates[start]),
                        start_index=start,
                        end_index=day_index - 1,
                    )
                    episode_index = len(episodes)
                    episodes.append(episode)
                    by_state_season.setdefault(
                        (state_index, episode.season),
                        [],
                    ).append(episode_index)
                    start = day_index if current else None
    return episodes, by_state_season


def _episode_supports(
    episode: Episode,
    *,
    target_flags: np.ndarray,
    dates: list[date],
    lag_days: int,
) -> bool:
    for source_index in range(episode.start_index, episode.end_index + 1):
        target_index = source_index + lag_days
        if target_index >= len(dates):
            continue
        if (dates[target_index] - dates[source_index]).days != lag_days:
            continue
        if _season(dates[target_index]) != episode.season:
            continue
        if target_flags[target_index, episode.tile_index]:
            return True
    return False


def _state_layer(spec: IndicatorStateSpec) -> str:
    dynamic_count = len(DYNAMIC_INDICATORS.intersection(spec.indicators))
    if dynamic_count == 0:
        return "observable"
    if dynamic_count == len(spec.indicators):
        return "dynamic"
    return "mixed"


def _state_season_coverage(
    aggregated: AggregatedIndicators,
    state_specs: tuple[IndicatorStateSpec, ...],
    config: BuildConfig,
) -> dict[str, dict[str, dict[str, Any]]]:
    coverage: dict[str, dict[str, dict[str, Any]]] = {}
    for spec in state_specs:
        coverage[spec.name] = {}
        for season in ("DJF", "MAM", "JJA", "SON"):
            indicator_coverage = {
                indicator: aggregated.seasonal_file_coverage.get(
                    indicator,
                    {},
                ).get(season, 0.0)
                for indicator in spec.indicators
            }
            minimum = min(indicator_coverage.values(), default=0.0)
            coverage[spec.name][season] = {
                "layer": _state_layer(spec),
                "indicator_coverage": indicator_coverage,
                "minimum_coverage": minimum,
                "coverage_gate_passed": (
                    minimum >= config.min_indicator_season_coverage
                ),
            }
    return coverage


def _extract_associations(
    aggregated: AggregatedIndicators,
    state_specs: tuple[IndicatorStateSpec, ...],
    state_flags: list[np.ndarray],
    availability: list[np.ndarray],
    episodes: list[Episode],
    episodes_by_state_season: dict[tuple[int, str], list[int]],
    state_season_coverage: dict[str, dict[str, dict[str, Any]]],
    config: BuildConfig,
) -> list[Association]:
    seasons = np.asarray([_season(day) for day in aggregated.dates])
    associations: list[Association] = []
    for source_index, source_spec in enumerate(state_specs):
        for target_index, target_spec in enumerate(state_specs):
            for season in ("DJF", "MAM", "JJA", "SON"):
                if not (
                    state_season_coverage[source_spec.name][season][
                        "coverage_gate_passed"
                    ]
                    and state_season_coverage[target_spec.name][season][
                        "coverage_gate_passed"
                    ]
                ):
                    continue
                source_episode_indices = episodes_by_state_season.get(
                    (source_index, season),
                    [],
                )
                if not source_episode_indices:
                    continue
                for lag_days in range(config.max_lag_days + 1):
                    if source_index == target_index and lag_days == 0:
                        continue
                    source_day_indices: list[int] = []
                    target_day_indices: list[int] = []
                    for day_index, day in enumerate(aggregated.dates):
                        target_day_index = day_index + lag_days
                        if target_day_index >= len(aggregated.dates):
                            continue
                        if (aggregated.dates[target_day_index] - day).days != lag_days:
                            continue
                        if seasons[day_index] != season or seasons[target_day_index] != season:
                            continue
                        source_day_indices.append(day_index)
                        target_day_indices.append(target_day_index)
                    if not source_day_indices:
                        continue
                    source_days = np.asarray(source_day_indices)
                    target_days = np.asarray(target_day_indices)
                    valid = (
                        availability[source_index][source_days]
                        & availability[target_index][target_days]
                    )
                    source = state_flags[source_index][source_days] & valid
                    target = state_flags[target_index][target_days] & valid
                    opportunity_count = int(valid.sum())
                    source_count = int(source.sum())
                    target_count = int(target.sum())
                    joint_count = int((source & target).sum())
                    if opportunity_count == 0 or source_count == 0 or target_count == 0:
                        continue
                    baseline_rate = target_count / opportunity_count
                    conditional_rate = joint_count / source_count
                    if baseline_rate <= 0:
                        continue
                    lift = conditional_rate / baseline_rate
                    support_indices: list[int] = []
                    counter_indices: list[int] = []
                    for episode_index in source_episode_indices:
                        if _episode_supports(
                            episodes[episode_index],
                            target_flags=state_flags[target_index],
                            dates=aggregated.dates,
                            lag_days=lag_days,
                        ):
                            support_indices.append(episode_index)
                        else:
                            counter_indices.append(episode_index)
                    if (
                        len(support_indices) < config.min_support_episodes
                        or lift < config.min_lift
                    ):
                        continue
                    associations.append(
                        Association(
                            source_state_index=source_index,
                            target_state_index=target_index,
                            season=season,
                            lag_days=lag_days,
                            opportunity_count=opportunity_count,
                            source_occurrence_count=source_count,
                            target_occurrence_count=target_count,
                            joint_occurrence_count=joint_count,
                            support_episode_indices=tuple(support_indices),
                            counterexample_episode_indices=tuple(counter_indices),
                            baseline_rate=baseline_rate,
                            conditional_rate=conditional_rate,
                            lift=lift,
                        )
                    )
    return _select_associations(
        associations,
        state_specs=state_specs,
        config=config,
    )


def _association_score(association: Association) -> float:
    return (association.lift - 1.0) * math.log1p(
        len(association.support_episode_indices)
    )


def _assess_association(
    association: Association,
    *,
    state_specs: tuple[IndicatorStateSpec, ...],
    config: BuildConfig,
):
    source = state_specs[association.source_state_index]
    target = state_specs[association.target_state_index]
    return assess_relation(
        source_concept_iri=source.concept_iri,
        target_concept_iri=target.concept_iri,
        source_phenomenon_family=source.phenomenon_family,
        target_phenomenon_family=target.phenomenon_family,
        target_is_extreme_weather=(
            target.ontology_class_iri == f"{MAZU}ExtremeWeatherState"
        ),
        lag_days=association.lag_days,
        support_episode_count=len(association.support_episode_indices),
        counterexample_episode_count=len(
            association.counterexample_episode_indices
        ),
        lift=association.lift,
        coverage_gate_passed=True,
        min_support_episodes=config.min_support_episodes,
        min_lift=config.min_lift,
        min_candidate_support_rate=config.min_candidate_support_rate,
    )


def _select_associations(
    associations: list[Association],
    *,
    state_specs: tuple[IndicatorStateSpec, ...],
    config: BuildConfig,
) -> list[Association]:
    """Keep qualified hazard candidates from being crowded out by persistence."""

    ranked = sorted(associations, key=_association_score, reverse=True)
    candidates: list[Association] = []
    remaining: list[Association] = []
    for association in ranked:
        assessment = _assess_association(
            association,
            state_specs=state_specs,
            config=config,
        )
        if assessment.eligible_for_prediction_experiment:
            candidates.append(association)
        else:
            remaining.append(association)
    return (candidates + remaining)[: config.max_assertions]


def _local_name(iri: str) -> str:
    return iri.rsplit(":", 1)[-1]


def _edge(
    build_id: str,
    sequence: int,
    source_id: str,
    predicate_iri: str,
    target_id: str,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "edge_id": f"urn:mazu-saudi:kg:{build_id}:edge:{sequence:08d}",
        "build_id": build_id,
        "source_id": source_id,
        "predicate_iri": predicate_iri,
        "target_id": target_id,
        "properties": properties or {},
    }


def _episode_multisource_context(
    aggregated: AggregatedIndicators,
    episode: Episode,
) -> dict[str, Any]:
    day_slice = slice(episode.start_index, episode.end_index + 1)
    tile_index = episode.tile_index
    summaries: dict[str, Any] = {}
    duration_days = episode.end_index - episode.start_index + 1
    for indicator in AUXILIARY_INDICATORS:
        if indicator not in aggregated.values:
            continue
        sample = aggregated.values[indicator][day_slice, tile_index]
        finite = sample[np.isfinite(sample)]
        if finite.size == 0:
            continue
        summaries[indicator] = {
            "mean": float(np.mean(finite)),
            "min": float(np.min(finite)),
            "max": float(np.max(finite)),
            "sample_days": int(finite.size),
            "source_products": [
                DATA_SOURCE_IRIS[key]
                for key in INDICATOR_SOURCE_KEYS.get(indicator, ())
            ],
            }

    def available_days(indicator: str) -> int:
        values = aggregated.values.get(indicator)
        if values is None:
            return 0
        return int(np.isfinite(values[day_slice, tile_index]).sum())

    summaries["data_availability"] = {
        "episode_days": duration_days,
        "ds1_monthly_background_days": available_days("monthly_precip_total"),
        "ds2_daily_precipitation_days": available_days("daily_precip_total"),
        "ds4_sst_days": available_days("sst_c"),
        "ds10_satellite_precipitation_days": available_days(
            "satellite_precip_total"
        ),
    }

    if (
        "daily_precip_total" in aggregated.values
        and "satellite_precip_total" in aggregated.values
        and "satellite_precip_coverage" in aggregated.values
    ):
        analysis = aggregated.values["daily_precip_total"][day_slice, tile_index]
        satellite = aggregated.values["satellite_precip_total"][day_slice, tile_index]
        coverage = aggregated.values["satellite_precip_coverage"][day_slice, tile_index]
        paired = (
            np.isfinite(analysis)
            & np.isfinite(satellite)
            & np.isfinite(coverage)
            & (coverage >= 0.95)
        )
        if np.any(paired):
            difference = satellite[paired] - analysis[paired]
            ratio = np.divide(
                satellite[paired],
                analysis[paired],
                out=np.full(int(paired.sum()), np.nan, dtype=np.float32),
                where=np.abs(analysis[paired]) > 1e-6,
            )
            summaries["precipitation_source_agreement"] = {
                "paired_days": int(paired.sum()),
                "mean_satellite_minus_analysis_mm": float(np.mean(difference)),
                "mean_absolute_difference_mm": float(np.mean(np.abs(difference))),
                "mean_satellite_to_analysis_ratio": (
                    float(np.nanmean(ratio))
                    if np.any(np.isfinite(ratio))
                    else None
                ),
                "claim_boundary": (
                    "Cross-source consistency diagnostic; neither source is treated "
                    "as an independently verified hazard event."
                ),
            }
    return summaries


def _materialize_records(
    *,
    build_id: str,
    aggregated: AggregatedIndicators,
    state_specs: tuple[IndicatorStateSpec, ...],
    thresholds: dict[tuple[int, str, int, str], tuple[float, int]],
    episodes: list[Episode],
    associations: list[Association],
    state_season_coverage: dict[str, dict[str, dict[str, Any]]],
    config: BuildConfig,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    run_id = f"urn:mazu-saudi:kg:{build_id}:run"
    nodes: list[dict[str, Any]] = [
        {
            "node_id": run_id,
            "build_id": build_id,
            "ontology_class_iri": f"{MAZU}ExtractionRun",
            "concept_iri": None,
            "label": f"{config.scope_label} 图谱提取运行",
            "spatial_key": config.scope_label,
            "start_time": aggregated.dates[0].isoformat(),
            "end_time": aggregated.dates[-1].isoformat(),
            "properties": {
                "config": asdict(config),
                "source_file_coverage": aggregated.file_coverage,
                "seasonal_indicator_file_coverage": (
                    aggregated.seasonal_file_coverage
                ),
                "source_quality_counts": aggregated.source_quality_counts,
                "state_season_coverage": state_season_coverage,
                "association_coverage_policy": (
                    "Suppress every state-pair season when either state's "
                    "minimum indicator coverage is below the configured gate."
                ),
                "quality_tier": (
                    "validation-degraded"
                    if config.allow_degraded_coverage
                    else "formal"
                ),
                "claim_boundary": (
                    "Degraded source coverage was explicitly accepted for "
                    "pipeline and interface validation; this build is not a "
                    "formal global mechanism graph."
                    if config.allow_degraded_coverage
                    else "Formal indicator coverage gates passed."
                ),
            },
        }
    ]
    edges: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    edge_sequence = 0

    used_source_keys = {"ds2"}
    for indicator in AUXILIARY_INDICATORS:
        if aggregated.file_coverage.get(indicator, 0.0) <= 0:
            continue
        used_source_keys.update(INDICATOR_SOURCE_KEYS.get(indicator, ()))
    for source_key in sorted(used_source_keys):
        edge_sequence += 1
        edges.append(
            _edge(
                build_id,
                edge_sequence,
                run_id,
                PROV_USED,
                DATA_SOURCE_IRIS[source_key],
                {
                    "role": source_key,
                    "file_coverage": max(
                        (
                            aggregated.file_coverage.get(indicator, 0.0)
                            for indicator, keys in INDICATOR_SOURCE_KEYS.items()
                            if source_key in keys
                        ),
                        default=0.0,
                    ),
                },
            )
        )

    context_ids: dict[str, str] = {}
    for season in ("DJF", "MAM", "JJA", "SON"):
        context_id = f"urn:mazu-saudi:kg:{build_id}:context:{season}"
        context_ids[season] = context_id
        nodes.append(
            {
                "node_id": context_id,
                "build_id": build_id,
                "ontology_class_iri": f"{MAZU}SeasonalContext",
                "concept_iri": None,
                "label": f"{config.scope_label} · {season}",
                "spatial_key": config.scope_label,
                "start_time": aggregated.dates[0].isoformat(),
                "end_time": aggregated.dates[-1].isoformat(),
                "properties": {
                    "season": season,
                    "tile_degrees": config.tile_degrees,
                    "scope": config.scope_label,
                    "indicator_file_coverage": {
                        indicator: coverage[season]
                        for indicator, coverage in (
                            aggregated.seasonal_file_coverage.items()
                        )
                        if season in coverage
                    },
                    "available_relation_states": [
                        spec.name
                        for spec in state_specs
                        if state_season_coverage[spec.name][season][
                            "coverage_gate_passed"
                        ]
                    ],
                    "suppressed_relation_states": {
                        spec.name: state_season_coverage[spec.name][season]
                        for spec in state_specs
                        if not state_season_coverage[spec.name][season][
                            "coverage_gate_passed"
                        ]
                    },
                },
            }
        )
        edge_sequence += 1
        edges.append(
            _edge(
                build_id,
                edge_sequence,
                context_id,
                PROV_WAS_GENERATED_BY,
                run_id,
            )
        )

    for (state_index, season, tile_index, indicator), (
        threshold,
        sample_count,
    ) in thresholds.items():
        threshold_rows.append(
            {
                "build_id": build_id,
                "context_id": context_ids[season],
                "spatial_key": aggregated.spatial_keys[tile_index],
                "state_concept_iri": state_specs[state_index].concept_iri,
                "indicator_name": indicator,
                "quantile": state_specs[state_index].quantile,
                "threshold_value": threshold if np.isfinite(threshold) else None,
                "sample_count": sample_count,
            }
        )

    selected_episode_indices: set[int] = set()
    for association in associations:
        selected_episode_indices.update(
            association.support_episode_indices[: config.evidence_episode_limit]
        )
        selected_episode_indices.update(
            association.counterexample_episode_indices[: config.evidence_episode_limit]
        )

    episode_node_ids: dict[int, str] = {}
    for episode_index in sorted(selected_episode_indices):
        episode = episodes[episode_index]
        spec = state_specs[episode.state_index]
        start = aggregated.dates[episode.start_index]
        end = aggregated.dates[episode.end_index]
        episode_id = (
            f"urn:mazu-saudi:kg:{build_id}:episode:{spec.name}:"
            f"{episode.tile_index}:{start:%Y%m%d}:{end:%Y%m%d}"
        )
        state_id = f"{episode_id}:state"
        episode_node_ids[episode_index] = episode_id
        multisource_context = _episode_multisource_context(aggregated, episode)
        indicator_summary = {
            indicator: {
                "mean": float(
                    np.nanmean(
                        aggregated.values[indicator][
                            episode.start_index : episode.end_index + 1,
                            episode.tile_index,
                        ]
                    )
                ),
                "max": float(
                    np.nanmax(
                        aggregated.values[indicator][
                            episode.start_index : episode.end_index + 1,
                            episode.tile_index,
                        ]
                    )
                ),
                "threshold": thresholds[
                    (episode.state_index, episode.season, episode.tile_index, indicator)
                ][0],
            }
            for indicator in spec.indicators
        }
        common = {
            "build_id": build_id,
            "spatial_key": aggregated.spatial_keys[episode.tile_index],
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }
        nodes.extend(
            [
                {
                    "node_id": episode_id,
                    **common,
                    "ontology_class_iri": f"{MAZU}WeatherEpisode",
                    "concept_iri": None,
                    "label": f"{spec.label_zh}天气过程 · {start}–{end}",
                    "properties": {
                        "season": episode.season,
                        "tile_center": [
                            float(aggregated.tile_latitudes[episode.tile_index]),
                            float(aggregated.tile_longitudes[episode.tile_index]),
                        ],
                        "duration_days": episode.end_index - episode.start_index + 1,
                        "multi_source_context": multisource_context,
                    },
                },
                {
                    "node_id": state_id,
                    **common,
                    "ontology_class_iri": spec.ontology_class_iri,
                    "concept_iri": spec.concept_iri,
                    "label": f"{spec.label_zh} · {start}–{end}",
                    "properties": {
                        "season": episode.season,
                        "indicators": indicator_summary,
                        "threshold_rule": f"tile-season quantile {spec.quantile:.2f}",
                        "multi_source_context": multisource_context,
                    },
                },
            ]
        )
        edge_sequence += 1
        edges.append(_edge(build_id, edge_sequence, episode_id, f"{MAZU}hasState", state_id))
        for node_id in (episode_id, state_id):
            edge_sequence += 1
            edges.append(
                _edge(
                    build_id,
                    edge_sequence,
                    node_id,
                    PROV_WAS_GENERATED_BY,
                    run_id,
                )
            )
        if spec.ontology_class_iri == f"{MAZU}IndicatorState":
            for indicator_iri in spec.indicator_iris:
                edge_sequence += 1
                edges.append(
                    _edge(
                        build_id,
                        edge_sequence,
                        state_id,
                        f"{MAZU}derivedFromIndicator",
                        indicator_iri,
                    )
                )
        source_keys = {
            source_key
            for indicator in spec.indicators
            for source_key in INDICATOR_SOURCE_KEYS.get(indicator, ())
        }
        if (
            "daily_precip_total" in spec.indicators
            and "satellite_precip_total" in multisource_context
        ):
            source_keys.add("ds10")
        for source_key in sorted(source_keys):
            edge_sequence += 1
            edges.append(
                _edge(
                    build_id,
                    edge_sequence,
                    state_id,
                    PROV_WAS_DERIVED_FROM,
                    DATA_SOURCE_IRIS[source_key],
                )
            )

    for association_index, association in enumerate(associations):
        source = state_specs[association.source_state_index]
        target = state_specs[association.target_state_index]
        source_coverage = state_season_coverage[source.name][association.season]
        target_coverage = state_season_coverage[target.name][association.season]
        association_layers = {_state_layer(source), _state_layer(target)}
        evidence_layer = (
            next(iter(association_layers))
            if len(association_layers) == 1
            else "mixed"
        )
        support_count = len(association.support_episode_indices)
        counterexample_count = len(association.counterexample_episode_indices)
        assessment = _assess_association(
            association,
            state_specs=state_specs,
            config=config,
        )
        assertion_id = (
            f"urn:mazu-saudi:kg:{build_id}:assertion:{association_index:04d}:"
            f"{source.name}:{target.name}:{association.season}:lag{association.lag_days}"
        )
        nodes.append(
            {
                "node_id": assertion_id,
                "build_id": build_id,
                "ontology_class_iri": f"{MAZU}LaggedAssociationAssertion",
                "concept_iri": None,
                "label": (
                    f"{source.label_zh} → {target.label_zh} "
                    f"({association.season}, +{association.lag_days}天)"
                ),
                "spatial_key": config.scope_label,
                "start_time": aggregated.dates[0].isoformat(),
                "end_time": aggregated.dates[-1].isoformat(),
                "properties": {
                    "lag_hours": association.lag_days * 24,
                    "lift": association.lift,
                    "support_episode_count": support_count,
                    "counterexample_episode_count": counterexample_count,
                    "support_rate": assessment.support_rate,
                    "evidence_class": "observational-statistical",
                    "evidence_layer": evidence_layer,
                    "relation_policy_version": RELATION_POLICY_VERSION,
                    "relation_role": assessment.relation_role,
                    "validation_stage": assessment.validation_stage,
                    "transferability_status": assessment.transferability_status,
                    "promotion_checks": assessment.promotion_checks,
                    "source_indicator_coverage": source_coverage,
                    "target_indicator_coverage": target_coverage,
                    "coverage_gate_passed": True,
                    "eligible_for_prediction_experiment": (
                        assessment.eligible_for_prediction_experiment
                    ),
                    "eligible_for_production_prediction": (
                        assessment.eligible_for_production_prediction
                    ),
                    "prediction_use": (
                        "Candidate for offline Saudi evaluation."
                        if assessment.eligible_for_prediction_experiment
                        else "Retained as evidence; not eligible as a prediction feature."
                    ),
                    "eligible_for_causal_explanation": False,
                },
            }
        )
        for predicate, target_id in (
            (f"{MAZU}sourceState", source.concept_iri),
            (f"{MAZU}targetState", target.concept_iri),
            (f"{MAZU}applicableUnder", context_ids[association.season]),
            (PROV_WAS_GENERATED_BY, run_id),
        ):
            edge_sequence += 1
            edges.append(
                _edge(build_id, edge_sequence, assertion_id, predicate, target_id)
            )
        for episode_index in association.support_episode_indices[
            : config.evidence_episode_limit
        ]:
            edge_sequence += 1
            edges.append(
                _edge(
                    build_id,
                    edge_sequence,
                    assertion_id,
                    f"{MAZU}supportedByEpisode",
                    episode_node_ids[episode_index],
                )
            )
        for episode_index in association.counterexample_episode_indices[
            : config.evidence_episode_limit
        ]:
            edge_sequence += 1
            edges.append(
                _edge(
                    build_id,
                    edge_sequence,
                    assertion_id,
                    f"{MAZU}contradictedByEpisode",
                    episode_node_ids[episode_index],
                )
            )
        evidence_rows.append(
            {
                "assertion_id": assertion_id,
                "build_id": build_id,
                "source_state_iri": source.concept_iri,
                "target_state_iri": target.concept_iri,
                "context_id": context_ids[association.season],
                "lag_days": association.lag_days,
                "opportunity_count": association.opportunity_count,
                "source_occurrence_count": association.source_occurrence_count,
                "target_occurrence_count": association.target_occurrence_count,
                "joint_occurrence_count": association.joint_occurrence_count,
                "support_episode_count": support_count,
                "counterexample_episode_count": counterexample_count,
                "baseline_rate": association.baseline_rate,
                "conditional_rate": association.conditional_rate,
                "lift": association.lift,
                "support_rate": assessment.support_rate,
                "evidence_class": "observational-statistical",
                "relation_policy_version": RELATION_POLICY_VERSION,
                "relation_role": assessment.relation_role,
                "validation_stage": assessment.validation_stage,
                "transferability_status": assessment.transferability_status,
                "eligible_for_prediction_experiment": int(
                    assessment.eligible_for_prediction_experiment
                ),
                "eligible_for_production_prediction": int(
                    assessment.eligible_for_production_prediction
                ),
                "eligible_for_causal_explanation": 0,
            }
        )
    return nodes, edges, evidence_rows, threshold_rows


def build_statistical_knowledge_graph(
    *,
    input_dir: Path,
    database_file: Path,
    config: BuildConfig = BuildConfig(),
    state_specs: tuple[IndicatorStateSpec, ...] = DEFAULT_STATE_SPECS,
) -> BuildResult:
    """Extract percentile states, episodes, and lagged associations into SQLite."""

    if not 0.0 < config.min_indicator_file_coverage <= 1.0:
        raise ValueError("min_indicator_file_coverage must be greater than 0 and at most 1")
    if not 0.0 < config.min_indicator_season_coverage <= 1.0:
        raise ValueError(
            "min_indicator_season_coverage must be greater than 0 and at most 1"
        )
    if not 0.0 <= config.min_candidate_support_rate <= 1.0:
        raise ValueError(
            "min_candidate_support_rate must be between 0 and 1"
        )
    if (
        config.allow_degraded_coverage
        and "validation-degraded" not in config.scope_label
    ):
        raise ValueError(
            "allow_degraded_coverage requires a scope_label containing "
            "'validation-degraded'"
        )

    input_dir = Path(input_dir).resolve()
    database_file = Path(database_file)
    files = discover_indicator_files(input_dir, config)
    store = KnowledgeGraphStore(database_file)
    store.initialize()
    ontology = store.ontology_identity()
    required_ontology_resources = {
        f"{MAZU}ExtractionRun",
        f"{MAZU}SeasonalContext",
        f"{MAZU}WeatherEpisode",
        f"{MAZU}LaggedAssociationAssertion",
        f"{MAZU}hasState",
        f"{MAZU}sourceState",
        f"{MAZU}targetState",
        f"{MAZU}applicableUnder",
        f"{MAZU}supportedByEpisode",
        f"{MAZU}contradictedByEpisode",
        f"{MAZU}derivedFromIndicator",
        *DATA_SOURCE_IRIS.values(),
    }
    for spec in state_specs:
        required_ontology_resources.update(
            {
                spec.ontology_class_iri,
                spec.concept_iri,
                *spec.indicator_iris,
            }
        )
    store.validate_ontology_resources(required_ontology_resources)

    aggregated = aggregate_daily_indicators(
        files,
        state_specs,
        tile_degrees=config.tile_degrees,
    )
    required_indicators = {
        indicator
        for spec in state_specs
        if spec.required_for_formal_graph
        for indicator in spec.indicators
    }
    insufficient_coverage = {
        indicator: coverage
        for indicator, coverage in aggregated.file_coverage.items()
        if indicator in required_indicators
        if coverage < config.min_indicator_file_coverage
    }
    if insufficient_coverage:
        raise ValueError(
            "Indicator file coverage is below "
            f"{config.min_indicator_file_coverage:.0%}: {insufficient_coverage}"
        )
    insufficient_seasonal_coverage = {
        indicator: {
            season: coverage
            for season, coverage in aggregated.seasonal_file_coverage[
                indicator
            ].items()
            if coverage < config.min_indicator_season_coverage
        }
        for indicator in sorted(required_indicators)
    }
    insufficient_seasonal_coverage = {
        indicator: seasons
        for indicator, seasons in insufficient_seasonal_coverage.items()
        if seasons
    }
    if insufficient_seasonal_coverage and not config.allow_degraded_coverage:
        raise ValueError(
            "Indicator seasonal file coverage is below "
            f"{config.min_indicator_season_coverage:.0%}: "
            f"{insufficient_seasonal_coverage}; use "
            "--allow-degraded-coverage only for an explicitly labelled "
            "validation graph"
        )
    state_flags, availability, thresholds = _derive_states(aggregated, state_specs)
    state_season_coverage = _state_season_coverage(
        aggregated,
        state_specs,
        config,
    )
    episodes, episodes_by_state_season = _extract_episodes(
        aggregated.dates,
        state_flags,
    )
    associations = _extract_associations(
        aggregated,
        state_specs,
        state_flags,
        availability,
        episodes,
        episodes_by_state_season,
        state_season_coverage,
        config,
    )
    build_id = (
        f"kg-{config.year}-"
        f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-"
        f"{uuid4().hex[:8]}"
    )
    nodes, edges, evidence, threshold_rows = _materialize_records(
        build_id=build_id,
        aggregated=aggregated,
        state_specs=state_specs,
        thresholds=thresholds,
        episodes=episodes,
        associations=associations,
        state_season_coverage=state_season_coverage,
        config=config,
    )
    validation_stage_counts: dict[str, int] = {}
    relation_role_counts: dict[str, int] = {}
    for row in evidence:
        validation_stage_counts[row["validation_stage"]] = (
            validation_stage_counts.get(row["validation_stage"], 0) + 1
        )
        relation_role_counts[row["relation_role"]] = (
            relation_role_counts.get(row["relation_role"], 0) + 1
        )
    selected_episode_count = sum(
        1 for node in nodes if node["ontology_class_iri"] == f"{MAZU}WeatherEpisode"
    )
    build = {
        "build_id": build_id,
        "ontology_iri": ontology["ontology_iri"],
        "ontology_version": ontology["version"],
        "ontology_sha256": ontology["source_sha256"],
        "input_root": str(input_dir),
        "input_manifest_sha256": _manifest_sha256(input_dir, files),
        "scope_label": config.scope_label,
        "start_date": files[0][0].isoformat(),
        "end_date": files[-1][0].isoformat(),
        "file_count": len(files),
        "config": {
            **asdict(config),
            "state_specs": [asdict(spec) for spec in state_specs],
            "input_fingerprint": "sha256(path,size,mtime_ns manifest)",
            "indicator_file_coverage": aggregated.file_coverage,
            "seasonal_indicator_file_coverage": (
                aggregated.seasonal_file_coverage
            ),
            "source_quality_counts": aggregated.source_quality_counts,
            "state_season_coverage": state_season_coverage,
            "association_coverage_policy": (
                "state-pair seasons below min_indicator_season_coverage "
                "are suppressed"
            ),
            "association_selection_policy": (
                "eligible Saudi evaluation candidates are ranked first, then "
                "remaining evidence by lift-support score, up to max_assertions"
            ),
            "relation_policy": {
                "version": RELATION_POLICY_VERSION,
                "principle": (
                    "Preserve all selected observational evidence, but only "
                    "cross-indicator lagged relations targeting an extreme-weather "
                    "state may become Saudi offline-evaluation candidates."
                ),
                "min_candidate_support_rate": config.min_candidate_support_rate,
                "automatic_causal_promotion": False,
                "automatic_production_promotion": False,
            },
            "relation_role_counts": relation_role_counts,
            "validation_stage_counts": validation_stage_counts,
            "quality_tier": (
                "validation-degraded"
                if config.allow_degraded_coverage
                else "formal"
            ),
            "seasonal_coverage_issues": insufficient_seasonal_coverage,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "assertion_count": len(associations),
        "episode_count": selected_episode_count,
    }
    store.write_build(
        build=build,
        nodes=nodes,
        edges=edges,
        evidence=evidence,
        thresholds=threshold_rows,
    )
    return BuildResult(
        build_id=build_id,
        database_file=str(database_file.resolve()),
        input_file_count=len(files),
        spatial_tile_count=len(aggregated.spatial_keys),
        node_count=len(nodes),
        edge_count=len(edges),
        assertion_count=len(associations),
        prediction_candidate_count=validation_stage_counts.get(
            "candidate_for_saudi_evaluation",
            0,
        ),
        diagnostic_assertion_count=validation_stage_counts.get(
            "diagnostic_evidence",
            0,
        ),
        episode_count=selected_episode_count,
        threshold_count=len(threshold_rows),
        start_date=files[0][0].isoformat(),
        end_date=files[-1][0].isoformat(),
    )
