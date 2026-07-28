"""Causal adapter for the 2025 Saudi T+1 precipitation-proxy experiment."""

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import torch

from .contracts import MCRPrecipBatch
from .priors import applicability_prior


FEATURE_VARS = (
    "daily_precip_total",
    "daily_convective_precip",
    "cape",
    "pwat",
    "ivt",
    "wind850_speed",
    "wind_shear_850_200",
    "sst_celsius",
)
LABEL_VAR = "flash_flood_risk"
LABEL_THRESHOLD = 2.0


@dataclass(frozen=True)
class SplitConfig:
    train_end: str = "2025-05-31"
    validation_start: str = "2025-06-01"
    validation_end: str = "2025-06-30"


@dataclass(frozen=True)
class SplitIndices:
    train: np.ndarray
    validation: np.ndarray
    test: np.ndarray


@dataclass(frozen=True)
class ChannelStats:
    median: np.ndarray
    mean: np.ndarray
    scale: np.ndarray


@dataclass
class PreparedProxyData:
    dynamic: torch.Tensor
    static: torch.Tensor
    mechanism: torch.Tensor
    availability: torch.Tensor
    occurrence: torch.Tensor
    rainfall: torch.Tensor
    lead_hours: torch.Tensor
    valid_dates: np.ndarray
    input_dates: np.ndarray
    split: SplitIndices
    feature_names: tuple[str, ...]
    channel_stats: ChannelStats
    terrain_available: bool

    def batch(self, indices: Sequence[int] | np.ndarray | torch.Tensor) -> MCRPrecipBatch:
        idx = torch.as_tensor(indices, dtype=torch.long)
        static = self.static.expand(idx.numel(), -1, -1, -1)
        return MCRPrecipBatch(
            dynamic=self.dynamic[idx],
            static=static,
            mechanism=self.mechanism[idx],
            availability=self.availability[idx],
            lead_hours=self.lead_hours[idx],
            occurrence=self.occurrence[idx],
            rainfall=self.rainfall[idx],
        )


def split_valid_dates(valid_dates: Sequence[str], config: SplitConfig = SplitConfig()) -> SplitIndices:
    dates = np.asarray(valid_dates, dtype="U10")
    train = np.flatnonzero(dates <= config.train_end)
    validation = np.flatnonzero(
        (dates >= config.validation_start) & (dates <= config.validation_end)
    )
    test = np.flatnonzero(dates > config.validation_end)
    if not train.size or not validation.size or not test.size:
        raise ValueError("train, validation, and test splits must all be non-empty")
    if np.intersect1d(train, validation).size or np.intersect1d(train, test).size:
        raise ValueError("time splits overlap")
    if config.validation_start <= config.train_end:
        raise ValueError("validation must start after training")
    return SplitIndices(train, validation, test)


def fit_channel_stats(dynamic: np.ndarray, train_indices: np.ndarray) -> ChannelStats:
    train = np.asarray(dynamic[train_indices], dtype=np.float32)
    median = np.nanmedian(train, axis=(0, 2, 3))
    median = np.where(np.isfinite(median), median, 0.0).astype(np.float32)
    filled = np.where(np.isfinite(train), train, median[None, :, None, None])
    mean = filled.mean(axis=(0, 2, 3), dtype=np.float64).astype(np.float32)
    scale = filled.std(axis=(0, 2, 3), dtype=np.float64).astype(np.float32)
    scale = np.where(scale > 1e-6, scale, 1.0).astype(np.float32)
    return ChannelStats(median, mean, scale)


def apply_channel_stats(dynamic: np.ndarray, stats: ChannelStats) -> np.ndarray:
    filled = np.where(
        np.isfinite(dynamic),
        dynamic,
        stats.median[None, :, None, None],
    )
    return ((filled - stats.mean[None, :, None, None]) / stats.scale[None, :, None, None]).astype(
        np.float32
    )


def _load_orography(dataset, source: str | Path | None, yi: np.ndarray, xi: np.ndarray):
    import xarray as xr

    if "orography" in dataset:
        values = dataset["orography"].values
        return np.asarray(values[np.ix_(yi, xi)], dtype=np.float32), True
    if source is None:
        return np.zeros((len(yi), len(xi)), dtype=np.float32), False
    with xr.open_dataset(source) as terrain:
        if "orography" not in terrain:
            raise ValueError("orography source does not contain 'orography'")
        if not np.array_equal(dataset.latitude.values, terrain.latitude.values):
            raise ValueError("orography latitude grid does not match consolidated dataset")
        if not np.array_equal(dataset.longitude.values, terrain.longitude.values):
            raise ValueError("orography longitude grid does not match consolidated dataset")
        values = terrain["orography"].values
    return np.asarray(values[np.ix_(yi, xi)], dtype=np.float32), True


def _availability(raw: np.ndarray, terrain_available: bool) -> np.ndarray:
    finite = np.isfinite(raw)
    precip = finite[:, :2].mean(axis=(1, 2, 3))
    atmosphere = finite[:, 2:7].mean(axis=(1, 2, 3))
    terrain = np.full(raw.shape[0], float(terrain_available), dtype=np.float32)
    return np.stack((precip, atmosphere, terrain), axis=1).astype(np.float32)


def _scaled_static(orography: np.ndarray) -> tuple[np.ndarray, float]:
    finite = np.isfinite(orography)
    if not finite.any():
        return np.zeros_like(orography, dtype=np.float32), 0.0
    median = float(np.nanmedian(orography))
    scale = float(np.nanpercentile(np.abs(orography - median), 90))
    if not np.isfinite(scale) or scale < 1e-6:
        scale = 1.0
    normalized = np.where(finite, (orography - median) / scale, 0.0).astype(np.float32)
    dx = np.diff(normalized, axis=1, append=normalized[:, -1:])
    dy = np.diff(normalized, axis=0, append=normalized[-1:, :])
    slope = float(np.nanpercentile(np.sqrt(dx * dx + dy * dy), 90))
    return normalized, slope


def _mechanism_state(normalized: np.ndarray, terrain_slope: float) -> np.ndarray:
    def unit_quantile(channel: int) -> np.ndarray:
        value = np.quantile(normalized[:, channel], 0.9, axis=(1, 2))
        return (1.0 / (1.0 + np.exp(-np.clip(value, -8, 8)))).astype(np.float32)

    n = normalized.shape[0]
    state = np.zeros((n, 8), dtype=np.float32)
    state[:, 2] = unit_quantile(FEATURE_VARS.index("ivt"))
    state[:, 3] = unit_quantile(FEATURE_VARS.index("cape"))
    state[:, 4] = unit_quantile(FEATURE_VARS.index("pwat"))
    state[:, 6] = 1.0 / (1.0 + np.exp(-min(max(terrain_slope, -8), 8)))
    state[:, 7] = unit_quantile(FEATURE_VARS.index("daily_precip_total"))
    return state


def prepare_proxy_data(
    dataset_path: str | Path,
    orography_source: str | Path | None = None,
    stride: int = 4,
    split_config: SplitConfig = SplitConfig(),
) -> PreparedProxyData:
    """Load a downsampled, train-normalized T+1 proxy dataset.

    The forecast valid date, rather than the input date, controls the split.
    The final source day has no observable T+1 label and is excluded.
    """

    import xarray as xr

    if stride < 1:
        raise ValueError("stride must be positive")
    with xr.open_dataset(dataset_path) as dataset:
        missing = [name for name in (*FEATURE_VARS, LABEL_VAR) if name not in dataset]
        if missing:
            raise ValueError(f"dataset missing required variables: {missing}")
        yi = np.arange(0, dataset.sizes["latitude"], stride)
        xi = np.arange(0, dataset.sizes["longitude"], stride)
        raw = np.stack(
            [dataset[name].values[:-1, yi][:, :, xi] for name in FEATURE_VARS],
            axis=1,
        ).astype(np.float32)
        label_raw = dataset[LABEL_VAR].values[1:, yi][:, :, xi].astype(np.float32)
        rainfall_raw = dataset["daily_precip_total"].values[1:, yi][:, :, xi].astype(np.float32)
        time_values = dataset.time.values.astype("datetime64[D]")
        input_dates = np.datetime_as_string(time_values[:-1], unit="D")
        valid_dates = np.datetime_as_string(time_values[1:], unit="D")
        orography, terrain_available = _load_orography(dataset, orography_source, yi, xi)

    split = split_valid_dates(valid_dates, split_config)
    stats = fit_channel_stats(raw, split.train)
    normalized = apply_channel_stats(raw, stats)
    doy = time_values[:-1].astype(object)
    day_of_year = np.array([value.timetuple().tm_yday for value in doy], dtype=np.float32)
    angle = 2 * np.pi * day_of_year / 365.25
    spatial_shape = normalized.shape[-2:]
    seasonal = np.stack((np.sin(angle), np.cos(angle)), axis=1)[:, :, None, None]
    seasonal = np.broadcast_to(seasonal, (len(angle), 2, *spatial_shape)).astype(np.float32)
    dynamic = np.concatenate((normalized, seasonal), axis=1)

    static, terrain_slope = _scaled_static(orography)
    occurrence = np.where(
        np.isfinite(label_raw),
        (label_raw >= LABEL_THRESHOLD).astype(np.float32),
        np.nan,
    )
    rainfall = np.where(np.isfinite(rainfall_raw), rainfall_raw, np.nan).astype(np.float32)
    availability = _availability(raw, terrain_available)
    mechanism = _mechanism_state(normalized, terrain_slope)
    prepared = PreparedProxyData(
        dynamic=torch.from_numpy(dynamic[:, None]),
        static=torch.from_numpy(static[None, None]),
        mechanism=torch.from_numpy(mechanism),
        availability=torch.from_numpy(availability),
        occurrence=torch.from_numpy(occurrence[:, None]),
        rainfall=torch.from_numpy(rainfall[:, None]),
        lead_hours=torch.full((len(valid_dates),), 24, dtype=torch.long),
        valid_dates=np.asarray(valid_dates),
        input_dates=np.asarray(input_dates),
        split=split,
        feature_names=(*FEATURE_VARS, "day_of_year_sin", "day_of_year_cos"),
        channel_stats=stats,
        terrain_available=terrain_available,
    )
    prepared.batch([0]).validate(mechanism_dim=8, availability_dim=3)
    return prepared


def routing_priors(data: PreparedProxyData, indices: Sequence[int] | np.ndarray) -> torch.Tensor:
    idx = torch.as_tensor(indices, dtype=torch.long)
    return applicability_prior(data.mechanism[idx])
