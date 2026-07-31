"""Similar historical events (初步设计.md 第4节 + 第5节 SIMILAR_TO edge).

v1 has no real event database or vector search; ``data/historical_events.py``
is a small static, hand-curated sample. Similarity is a simple deterministic
score combining hazard match (required), region match, and closeness between
the current calibrated probability and the event's reference probability —
good enough to demonstrate the "similar historical events" explanation slot
without pretending to run real case-based retrieval.
"""

from __future__ import annotations

from app.schemas.prediction import HistoricalEvent
from data.historical_events import HISTORICAL_EVENTS, HistoricalEventRecord


def _similarity(record: HistoricalEventRecord, region_id: str, calibrated_probability: float) -> float:
    score = 0.5
    if record.region_id == region_id:
        score += 0.25
    score += 0.25 * (1 - min(abs(record.reference_probability - calibrated_probability), 1.0))
    return round(min(score, 0.99), 2)


def find_similar_events(
    hazard: str, region_id: str, calibrated_probability: float, limit: int = 3
) -> list[HistoricalEvent]:
    candidates = [rec for rec in HISTORICAL_EVENTS if rec.hazard == hazard]
    scored = sorted(
        candidates,
        key=lambda rec: _similarity(rec, region_id, calibrated_probability),
        reverse=True,
    )[:limit]
    return [
        HistoricalEvent(
            event_id=rec.event_id,
            date=rec.date,
            region=rec.region_name,
            hazard=rec.hazard_label,
            description=rec.description,
            similarity=_similarity(rec, region_id, calibrated_probability),
            max_rainfall=rec.max_rainfall,
            max_temp=rec.max_temp,
            impact=rec.impact,
        )
        for rec in scored
    ]
