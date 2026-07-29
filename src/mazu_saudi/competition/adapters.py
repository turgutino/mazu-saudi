"""Adapters around the verified historical warning tools."""

from __future__ import annotations

import importlib.util
import math
import os
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from .settings import AppSettings

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


CITIES = ("Jeddah", "Mecca", "Riyadh", "Jizan", "Dammam", "Taif", "Medina", "Abha")
HAZARDS = ("heatwave", "flash_flood", "dust_storm")


class WarningAdapter(Protocol):
    def forecast(self, city: str, target_date: str, hazard: str) -> dict[str, Any]: ...
    def conditions(self, city: str, date: str) -> dict[str, Any]: ...
    def evidence(self, hazard: str) -> dict[str, Any]: ...
    def cap(self, city: str, target_date: str, hazard: str) -> dict[str, Any]: ...
    def field(self, target_date: str, hazard: str, layer: str) -> dict[str, Any]: ...


class HistoricalToolAdapter:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._tools = None
        self._field_cache: dict[tuple[str, str, str], dict[str, Any]] = {}

    def _load_tools(self):
        if self._tools is None:
            path = self.settings.warning_root / "agent" / "tools.py"
            spec = importlib.util.spec_from_file_location("mazu_historical_tools", path)
            if spec is None or spec.loader is None:
                raise RuntimeError("Unable to load historical warning tools")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._tools = module
        return self._tools

    def forecast(self, city: str, target_date: str, hazard: str) -> dict[str, Any]:
        result = self._load_tools().forecast_tool(city, target_date, hazard)
        if "error" in result:
            raise ValueError(result["error"])
        return result

    def conditions(self, city: str, date: str) -> dict[str, Any]:
        result = self._load_tools().conditions_tool(city, date)
        if "error" in result:
            raise ValueError(result["error"])
        return result

    def evidence(self, hazard: str) -> dict[str, Any]:
        result = self._load_tools().causal_kg_tool(hazard)
        if "error" in result:
            raise ValueError(result["error"])
        return result

    def cap(self, city: str, target_date: str, hazard: str) -> dict[str, Any]:
        result = self._load_tools().cap_alert_tool(city, target_date, hazard)
        if "error" in result:
            raise ValueError(result["error"])
        return result

    def field(self, target_date: str, hazard: str, layer: str) -> dict[str, Any]:
        key = (target_date, hazard, layer)
        if key in self._field_cache:
            return {**self._field_cache[key], "cache": "hit"}
        tools = self._load_tools()
        meta, dataset = tools._load_resources()
        times = np.array([str(value)[:10] for value in dataset.time.values])
        if target_date not in times:
            raise ValueError(f"Date '{target_date}' not in 2025 historical dataset")
        target_index = int(np.where(times == target_date)[0][0])
        if target_index == 0:
            raise ValueError("No prior-day inputs are available for 2025-01-01")
        feature_index = target_index - 1
        feature_date = times[feature_index]
        stride = int(meta["stride"])
        lat_full, lon_full = dataset.latitude.values, dataset.longitude.values
        yi = np.arange(0, len(lat_full), stride)
        xi = np.arange(0, len(lon_full), stride)
        latitudes, longitudes = lat_full[yi], lon_full[xi]

        if layer == "rule_risk":
            full = tools._get_detection_engine().risk_field(feature_date, hazard)
            values = np.asarray(full)[yi][:, xi]
        else:
            raw = {
                name: dataset[name].values[feature_index][yi][:, xi]
                for name in tools.FEATURE_VARS
            }
            columns = [raw[name].reshape(-1) for name in tools.FEATURE_VARS]
            if hazard == "heatwave":
                columns.extend(
                    tools.neighbor_mean(raw[name]).reshape(-1)
                    for name in tools.NEIGHBOR_VARS
                )
            elif hazard == "dust_storm":
                columns.extend(
                    dataset[name].values[feature_index][yi][:, xi].reshape(-1)
                    for name in tools.DUST_EXTRA_VARS
                )
            lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing="ij")
            day_of_year = dataset.time.values[feature_index].astype("datetime64[D]").item().timetuple().tm_yday
            columns.extend(
                (
                    lat_grid.reshape(-1),
                    lon_grid.reshape(-1),
                    np.full(lat_grid.size, day_of_year),
                )
            )
            matrix = np.column_stack(columns)
            if layer == "probability":
                values = tools._get_model(hazard).predict_proba(matrix)[:, 1].reshape(lat_grid.shape)
            elif layer == "uncertainty":
                members = tools._get_ensemble_models(hazard)
                member_values = np.stack(
                    [model.predict_proba(matrix)[:, 1] for model in members], axis=0
                )
                values = member_values.std(axis=0).reshape(lat_grid.shape)
            else:
                raise ValueError(f"Unknown field layer '{layer}'")

        clean = np.where(np.isfinite(values), values, 0.0)
        payload = {
            "target_date": target_date,
            "features_from_date": feature_date,
            "hazard": hazard,
            "layer": layer,
            "rows": int(clean.shape[0]),
            "columns": int(clean.shape[1]),
            "latitudes": [round(float(value), 3) for value in latitudes],
            "longitudes": [round(float(value), 3) for value in longitudes],
            "values": [round(float(value), 5) for value in clean.reshape(-1)],
            "minimum": round(float(clean.min()), 5),
            "maximum": round(float(clean.max()), 5),
            "cache": "miss",
            "boundary": "2025 historical exercise; not an operational warning",
        }
        self._field_cache[key] = payload
        return payload


def level_for_probability(tools: Any, hazard: str, probability: float) -> tuple[str, float]:
    rule = tools.DETECTION_RULES[hazard]
    level = rule["severity"][0][0]
    for name, lower_bound in rule["severity"]:
        if probability >= lower_bound:
            level = name
    return level, float(rule["severity"][1][1])


def finite_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: finite_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [finite_json(item) for item in value]
    if isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value
