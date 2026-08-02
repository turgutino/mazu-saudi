"""Format model-native local attributions without changing their meaning."""

from __future__ import annotations

import math

from app.data.indicator_provider import INDICATOR_SPECS
from app.domain.prediction import RawPrediction
from app.schemas.prediction import FeatureContribution


FEATURE_ALIASES = {
    "daily_precip_total": "daily_precip",
    "t2m_c": "t2m",
    "pwat": "pw",
    "wind10_speed": "wind_10m",
}

FEATURE_LABELS = {
    "daily_precip_total": ("24小时累计降水", "mm"),
    "daily_convective_precip": ("24小时对流降水", "mm"),
    "daily_large_scale_precip": ("24小时大尺度降水", "mm"),
    "t2m_c": ("24小时平均2m气温", "°C"),
    "tmax_c": ("24小时最高2m气温", "°C"),
    "tmin_c": ("24小时最低2m气温", "°C"),
    "heat_index_c": ("体感温度", "°C"),
    "vpd_kpa": ("饱和水汽压差", "kPa"),
    "cape": ("CAPE", "J/kg"),
    "pwat": ("可降水量", "mm"),
    "ivt": ("整层水汽输送", "kg/(m·s)"),
    "wind850_speed": ("850hPa风速", "m/s"),
    "wind_shear_850_200": ("850–200hPa风切变", "m/s"),
    "daily_precip_anomaly": ("日降水距平", "mm"),
    "t2m_anomaly_c": ("2m气温距平", "°C"),
    "tmax_anomaly_c": ("最高气温距平", "°C"),
    "sst_celsius": ("海表温度", "°C"),
    "wind10_speed": ("24小时平均10m风速", "m/s"),
    "dewpoint_depression_c": ("露点差", "°C"),
    "lat": ("纬度", "°"),
    "lon": ("经度", "°"),
    "day_of_year": ("年内日序", "day"),
}

FEATURE_LABELS_EN = {
    "daily_precip_total": ("24h Total Precip", "mm"),
    "daily_convective_precip": ("24h Convective Precip", "mm"),
    "daily_large_scale_precip": ("24h Large-Scale Precip", "mm"),
    "t2m_c": ("24h Mean 2m Temp", "°C"),
    "tmax_c": ("24h Max 2m Temp", "°C"),
    "tmin_c": ("24h Min 2m Temp", "°C"),
    "heat_index_c": ("Heat Index", "°C"),
    "vpd_kpa": ("Vapor Pressure Deficit", "kPa"),
    "cape": ("CAPE", "J/kg"),
    "pwat": ("Precipitable Water", "mm"),
    "ivt": ("Integrated Vapor Transport", "kg/(m·s)"),
    "wind850_speed": ("850hPa Wind Speed", "m/s"),
    "wind_shear_850_200": ("850-200hPa Wind Shear", "m/s"),
    "daily_precip_anomaly": ("Daily Precip Anomaly", "mm"),
    "t2m_anomaly_c": ("2m Temp Anomaly", "°C"),
    "tmax_anomaly_c": ("Max Temp Anomaly", "°C"),
    "sst_celsius": ("Sea Surface Temp", "°C"),
    "wind10_speed": ("24h Mean 10m Wind Speed", "m/s"),
    "dewpoint_depression_c": ("Dewpoint Depression", "°C"),
    "lat": ("Latitude", "°"),
    "lon": ("Longitude", "°"),
    "day_of_year": ("Day of Year", "day"),
}


def _display_metadata(feature: str, lang: str = "zh") -> tuple[str, str, float | None]:
    base_feature = feature.removeprefix("neigh_")
    alias = FEATURE_ALIASES.get(base_feature, base_feature)
    spec = INDICATOR_SPECS.get(alias)
    labels_table = FEATURE_LABELS_EN if lang == "en" else FEATURE_LABELS
    label, unit = labels_table.get(
        base_feature,
        (base_feature.replace("_", " "), spec.unit if spec else ""),
    )
    if feature.startswith("neigh_"):
        label = f"Neighborhood {label}" if lang == "en" else f"邻域{label}"
    return label, unit, spec.normal_value if spec else None


def build_feature_contributions(
    prediction: RawPrediction, indicators: dict[str, float], lang: str = "zh"
) -> list[FeatureContribution]:
    """Rank by absolute attribution and retain every explained model input."""

    ranked = sorted(
        prediction.important_features.items(), key=lambda kv: abs(kv[1]), reverse=True
    )
    contributions: list[FeatureContribution] = []
    for key, contribution in ranked:
        if key not in indicators:
            continue
        label, unit, normal_value = _display_metadata(key, lang)
        actual_value = float(indicators[key])
        contributions.append(
            FeatureContribution(
                feature=key,
                feature_label=label,
                contribution=contribution,
                normal_value=normal_value,
                actual_value=actual_value if math.isfinite(actual_value) else None,
                unit=unit,
            )
        )
    return contributions
