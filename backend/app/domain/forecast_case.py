"""ForecastCase: the single framework-agnostic input object for all models.

See 初步设计.md 第1节 (数据准备层). Every prediction run starts by building a
ForecastCase; its ``input_hash`` makes the run reproducible: the very same
(region, hazard, lead time, initial time, feature version) tuple always
produces the same hash, which downstream components (indicator provider,
model) use as a deterministic seed instead of inventing random numbers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

FEATURE_VERSION = "v1"


def compute_input_hash(
    region_id: str,
    hazard: str,
    lead_time_hours: int,
    initial_time: datetime,
    feature_version: str = FEATURE_VERSION,
) -> str:
    payload = "|".join(
        [region_id, hazard, str(lead_time_hours), initial_time.isoformat(), feature_version]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ForecastCase:
    case_id: str
    initial_time: datetime
    target_time: datetime
    lead_time_hours: int
    region_id: str
    hazard: str
    input_hash: str
    feature_version: str = FEATURE_VERSION
    features: dict[str, float] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        case_id: str,
        region_id: str,
        hazard: str,
        lead_time_hours: int,
        initial_time: datetime | None = None,
        feature_version: str = FEATURE_VERSION,
    ) -> "ForecastCase":
        initial_time = initial_time or datetime.now(timezone.utc)
        target_time = initial_time + timedelta(hours=lead_time_hours)
        input_hash = compute_input_hash(
            region_id, hazard, lead_time_hours, initial_time, feature_version
        )
        return cls(
            case_id=case_id,
            initial_time=initial_time,
            target_time=target_time,
            lead_time_hours=lead_time_hours,
            region_id=region_id,
            hazard=hazard,
            input_hash=input_hash,
            feature_version=feature_version,
        )

    @property
    def seed(self) -> int:
        """Deterministic 32-bit seed derived from input_hash."""
        return int(self.input_hash[:8], 16)
