"""Framework-independent forecast contract and deterministic demo backend."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import math
import random
from typing import Any


REGIONS = {
    "arabian_peninsula": {"label": "Arabian Peninsula", "label_zh": "阿拉伯半岛", "bbox": [16.0, 34.0, 32.0, 56.0]},
    "southwest_us": {"label": "Southwest United States", "label_zh": "美国西南", "bbox": [28.0, -116.0, 38.0, -102.0]},
    "interior_australia": {"label": "Interior Australia", "label_zh": "澳大利亚内陆", "bbox": [-31.0, 124.0, -18.0, 139.0]},
    "southern_africa": {"label": "Southern Africa", "label_zh": "南部非洲", "bbox": [-30.0, 15.0, -18.0, 31.0]},
}


@dataclass(frozen=True)
class ForecastRequest:
    region: str = "arabian_peninsula"
    lead_hours: int = 1

    def validate(self) -> None:
        if self.region not in REGIONS:
            raise ValueError(f"unknown region: {self.region}")
        if self.lead_hours not in (1, 3, 6):
            raise ValueError("lead_hours must be 1, 3, or 6")


class DemoForecastService:
    """Generate stable, realistic-looking payloads without claiming evidence."""

    mode = "demo"
    scientific_evidence = False
    model_version = "mcr-precip-core-v0.1"
    data_version = "synthetic-product-demo-v1"
    forecast_origin = "2025-09-02T18:00:00Z"

    def config(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "scientific_evidence": self.scientific_evidence,
            "model_version": self.model_version,
            "data_version": self.data_version,
            "forecast_origin": self.forecast_origin,
            "leads": [1, 3, 6],
            "regions": [{"id": key, **value} for key, value in REGIONS.items()],
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "mode": self.mode,
            "model_loaded": False,
            "scientific_evidence": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def forecast(self, request: ForecastRequest) -> dict[str, Any]:
        request.validate()
        region = REGIONS[request.region]
        cells = self._cells(request)
        maximum = max(cell["probability"] for cell in cells)
        mean_probability = sum(cell["probability"] for cell in cells) / len(cells)
        routing = self._routing(request)
        uncertainty = min(0.42, 0.13 + request.lead_hours * 0.025)
        abstain = request.lead_hours == 6 and request.region == "southern_africa"
        return {
            "contract_version": "forecast-response-v1",
            "mode": self.mode,
            "scientific_evidence": self.scientific_evidence,
            "forecast_origin": self.forecast_origin,
            "valid_time": self._valid_time(request.lead_hours),
            "region": {"id": request.region, **region},
            "lead_hours": request.lead_hours,
            "model": {"name": "MCR-Precip", "version": self.model_version},
            "data_version": self.data_version,
            "summary": {
                "max_probability": round(maximum, 3),
                "mean_probability": round(mean_probability, 3),
                "p50_rainfall_mm": round(4.8 + maximum * 22 + request.lead_hours * 0.8, 1),
                "p90_rainfall_mm": round(12.5 + maximum * 44 + request.lead_hours * 1.6, 1),
                "uncertainty": round(uncertainty, 3),
                "selective_coverage": 0.72 if abstain else round(0.94 - request.lead_hours * 0.025, 2),
                "status": "abstain" if abstain else "forecast",
            },
            "routing": routing,
            "cells": cells,
            "sources": self._sources(request),
            "audit": {
                "availability_cutoff": self.forecast_origin,
                "region_id_used_by_router": False,
                "threshold_tuned_on_test": False,
                "note": "Deterministic demonstration payload; not a real forecast.",
            },
        }

    def events(self) -> list[dict[str, Any]]:
        return [
            {"time": "18:00", "type": "ingest", "title": "Forecast origin frozen", "detail": "All inputs passed availability-time checks."},
            {"time": "18:03", "type": "model", "title": "Mechanism routing complete", "detail": "Four propagation experts evaluated for three lead times."},
            {"time": "18:05", "type": "quality", "title": "Selective forecast check", "detail": "High-uncertainty cells flagged for review."},
            {"time": "18:08", "type": "publish", "title": "Demonstration product published", "detail": "DEMO payload only; no operational warning issued."},
        ]

    def _valid_time(self, lead: int) -> str:
        origin = datetime.fromisoformat(self.forecast_origin.replace("Z", "+00:00"))
        return (origin + timedelta(hours=lead)).isoformat().replace("+00:00", "Z")

    def _routing(self, request: ForecastRequest) -> list[dict[str, Any]]:
        region_bias = {
            "arabian_peninsula": (0.29, 0.34, 0.25, 0.12),
            "southwest_us": (0.24, 0.29, 0.34, 0.13),
            "interior_australia": (0.32, 0.25, 0.18, 0.25),
            "southern_africa": (0.27, 0.38, 0.17, 0.18),
        }[request.region]
        persistence_shift = request.lead_hours * 0.012
        raw = [region_bias[0], region_bias[1], region_bias[2], max(0.04, region_bias[3] - persistence_shift)]
        total = sum(raw)
        labels = (("advection", "平流传播"), ("convection", "局地对流"), ("orography", "地形抬升"), ("persistence", "持续衰减"))
        return [{"id": item[0], "label": item[1], "weight": round(value / total, 3)} for item, value in zip(labels, raw)]

    def _sources(self, request: ForecastRequest) -> list[dict[str, Any]]:
        atmosphere = "conflicting" if request.region == "southern_africa" and request.lead_hours == 6 else "observed"
        return [
            {"id": "recent_precipitation", "label": "Recent precipitation", "source": "FYMERG / IMERG adapter", "status": "observed", "freshness_minutes": 18},
            {"id": "atmosphere", "label": "Atmospheric state", "source": "MAZU forecast adapter", "status": atmosphere, "freshness_minutes": 42},
            {"id": "terrain", "label": "Terrain", "source": "Static DEM", "status": "observed", "freshness_minutes": None},
            {"id": "stations", "label": "Independent gauges", "source": "Evaluation-only", "status": "not_observable", "freshness_minutes": None},
        ]

    def _cells(self, request: ForecastRequest) -> list[dict[str, float]]:
        rows, columns = 18, 24
        seed = sum(ord(char) for char in request.region) + request.lead_hours * 101
        rng = random.Random(seed)
        centers = {
            "arabian_peninsula": ((0.28, 0.38, 0.13), (0.64, 0.62, 0.19), (0.48, 0.78, 0.11)),
            "southwest_us": ((0.24, 0.58, 0.16), (0.62, 0.42, 0.21)),
            "interior_australia": ((0.35, 0.52, 0.22), (0.74, 0.68, 0.13)),
            "southern_africa": ((0.48, 0.36, 0.19), (0.67, 0.72, 0.17)),
        }[request.region]
        cells = []
        lat0, lon0, lat1, lon1 = REGIONS[request.region]["bbox"]
        for row in range(rows):
            y = row / (rows - 1)
            for column in range(columns):
                x = column / (columns - 1)
                signal = 0.035
                for cx, cy, scale in centers:
                    distance = ((x - cx) ** 2 + (y - cy) ** 2) / (2 * scale**2)
                    signal += 0.72 * math.exp(-distance)
                signal *= 1 - request.lead_hours * 0.035
                signal += rng.uniform(-0.025, 0.025)
                probability = max(0.01, min(0.96, signal))
                uncertainty = min(0.5, 0.1 + request.lead_hours * 0.025 + abs(0.5 - probability) * 0.12)
                cells.append({
                    "row": row,
                    "column": column,
                    "latitude": round(lat1 - y * (lat1 - lat0), 3),
                    "longitude": round(lon0 + x * (lon1 - lon0), 3),
                    "probability": round(probability, 3),
                    "uncertainty": round(uncertainty, 3),
                })
        return cells
