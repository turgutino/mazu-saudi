"""Train API-compatible HGB postprocessors from 2025 daily indicator files."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import sklearn
import xarray as xr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)

FEATURES = [
    "daily_precip_total",
    "t2m_c",
    "tmax_c",
    "tmin_c",
    "wind10_speed",
    "lat",
    "lon",
    "day_of_year",
]
WEATHER_FEATURES = FEATURES[:5]
HAZARDS = {
    "heavy-rain": "heavy_rain",
    "extreme-heat": "heatwave",
    "flash-flood": "flash_flood",
    "dust-storm": "dust_storm",
}
LABEL_METADATA = {
    "heavy-rain": {
        "label": "daily_precip_total >= 25 mm",
        "label_type": "proxy",
        "label_source": "2025 archived target-day precipitation",
    },
    "extreme-heat": {
        "label": "heatwave_day_flag >= 1",
        "label_type": "provided",
        "label_source": "2025 archive heatwave_day_flag",
    },
    "flash-flood": {
        "label": "flash_flood_risk >= 2",
        "label_type": "provided_proxy",
        "label_source": "2025 archive flash_flood_risk teacher composite",
    },
    "dust-storm": {
        "label": "DetectionEngine dust_storm risk >= 0.55",
        "label_type": "proxy",
        "label_source": "2025 archive indicators + versioned detection rule",
    },
}


def _dust_label(ds: xr.Dataset, sample: tuple[slice, slice], shape: tuple[int, int]) -> np.ndarray:
    conditions = [
        ("wind10_speed", 7.0, 0.35),
        ("wind850_speed", 11.0, 0.25),
        ("dewpoint_depression_c", 38.0, 0.20),
        ("vpd_kpa", 5.5, 0.20),
    ]
    score = np.zeros(shape, dtype="float32")
    available_weight = np.zeros(shape, dtype="float32")
    for name, threshold, weight in conditions:
        if name not in ds:
            continue
        values = np.asarray(ds[name].values[sample], dtype="float32")
        valid = np.isfinite(values)
        score += np.where(valid, values >= threshold, False).astype("float32") * weight
        available_weight += valid.astype("float32") * weight
    normalized = np.divide(
        score,
        available_weight,
        out=np.zeros_like(score),
        where=available_weight > 0,
    )
    return normalized >= 0.55


def _labels(ds: xr.Dataset, sample: tuple[slice, slice]) -> dict[str, np.ndarray]:
    precipitation = np.asarray(ds["daily_precip_total"].values[sample])
    shape = precipitation.shape
    return {
        "heavy-rain": precipitation >= 25.0,
        "extreme-heat": np.asarray(ds["heatwave_day_flag"].values[sample]) >= 1,
        "flash-flood": np.asarray(ds["flash_flood_risk"].values[sample]) >= 2,
        "dust-storm": _dust_label(ds, sample, shape),
    }


def build_dataset(
    indicators_dir: Path, stride: int
) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray, list[str]]:
    paths = sorted(
        path
        for path in indicators_dir.glob("saudi_indicators_2025*.nc")
        if not path.name.startswith("._")
    )
    if len(paths) != 365:
        raise RuntimeError(f"Expected 365 daily indicator files, found {len(paths)}")

    rows: list[np.ndarray] = []
    dates: list[np.ndarray] = []
    labels: dict[str, list[np.ndarray]] = {hazard: [] for hazard in HAZARDS}
    skipped_days: list[str] = []
    sample = (slice(None, None, stride), slice(None, None, stride))
    for path in paths:
        date_text = path.stem.rsplit("_", 1)[-1]
        archive_date = datetime.strptime(date_text, "%Y%m%d")
        day_of_year = archive_date.timetuple().tm_yday
        with xr.open_dataset(path) as ds:
            required = WEATHER_FEATURES + [
                "latitude",
                "longitude",
                "heatwave_day_flag",
                "flash_flood_risk",
            ]
            missing = [name for name in required if name not in ds]
            if missing:
                skipped_days.append(f"{path.name}: {', '.join(missing)}")
                continue
            lat = np.asarray(ds["latitude"].values[sample[0]], dtype="float32")
            lon = np.asarray(ds["longitude"].values[sample[1]], dtype="float32")
            lat2, lon2 = np.meshgrid(lat, lon, indexing="ij")
            feature_arrays = [
                np.asarray(ds[name].values[sample], dtype="float32")
                for name in WEATHER_FEATURES
            ]
            feature_arrays.extend(
                [
                    lat2.astype("float32"),
                    lon2.astype("float32"),
                    np.full(lat2.shape, day_of_year, dtype="float32"),
                ]
            )
            stacked = np.stack(feature_arrays, axis=-1).reshape(-1, len(FEATURES))
            valid = np.all(np.isfinite(stacked), axis=1)
            if not np.any(valid):
                continue
            rows.append(stacked[valid])
            dates.append(np.full(valid.sum(), int(date_text), dtype="int32"))
            day_labels = _labels(ds, sample)
            for hazard, values in day_labels.items():
                selected = values.reshape(-1)[valid]
                if not np.all(np.isfinite(selected)):
                    raise RuntimeError(f"{path.name} contains non-finite {hazard} labels")
                labels[hazard].append(selected.astype("int8"))

    return (
        np.concatenate(rows),
        {hazard: np.concatenate(parts) for hazard, parts in labels.items()},
        np.concatenate(dates),
        skipped_days,
    )


def _metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    predicted = probability >= 0.5
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    pod = tp / (tp + fn) if tp + fn else 0.0
    far = fp / (tp + fp) if tp + fp else 0.0
    csi = tp / (tp + fp + fn) if tp + fp + fn else 0.0
    precision = 1.0 - far
    f1 = 2 * precision * pod / (precision + pod) if precision + pod else 0.0
    return {
        "auc": float(roc_auc_score(y, probability)),
        "pr_auc": float(average_precision_score(y, probability)),
        "pod": float(pod),
        "far": float(far),
        "csi": float(csi),
        "f1": float(f1),
        "brier": float(brier_score_loss(y, probability)),
    }


def train(indicators_dir: Path, output_dir: Path, stride: int = 4) -> dict:
    X, labels, dates, skipped_days = build_dataset(indicators_dir, stride)
    train_mask = dates <= 20250630
    test_mask = ~train_mask
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "feature_version": "live-api-daily-v1",
        "estimator": "HistGradientBoostingClassifier",
        "sklearn_version": sklearn.__version__,
        "features": FEATURES,
        "train_end": "2025-06-30",
        "stride": stride,
        "skipped_days": skipped_days,
        "models": {},
    }
    for hazard, artifact_key in HAZARDS.items():
        y = labels[hazard]
        if len(np.unique(y[train_mask])) != 2 or len(np.unique(y[test_mask])) != 2:
            raise RuntimeError(f"{hazard} does not have both classes in train and test")
        estimator = HistGradientBoostingClassifier(
            max_iter=120,
            max_depth=5,
            learning_rate=0.08,
            class_weight="balanced",
            random_state=42,
            early_stopping=True,
        )
        estimator.fit(X[train_mask], y[train_mask])
        probability = estimator.predict_proba(X[test_mask])[:, 1]
        joblib.dump(estimator, output_dir / f"live_api_{artifact_key}_model.joblib")
        metadata["models"][hazard] = {
            "artifact_key": artifact_key,
            **LABEL_METADATA[hazard],
            "train_samples": int(train_mask.sum()),
            "test_samples": int(test_mask.sum()),
            "train_positive_rate": float(y[train_mask].mean()),
            "test_positive_rate": float(y[test_mask].mean()),
            "metrics": _metrics(y[test_mask], probability),
        }
    with open(output_dir / "live_api_model_meta.json", "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indicators-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "app" / "models" / "artifacts",
    )
    parser.add_argument("--stride", type=int, default=4)
    args = parser.parse_args()
    metadata = train(args.indicators_dir, args.output_dir, args.stride)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
