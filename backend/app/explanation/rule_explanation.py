"""Risk decision explanation (初步设计.md 第4节: 风险决策解释).

Formats the ``RuleHitRecord`` list already produced by ``RiskPolicy.assess``
(app/risk/policy.py) into the API-facing ``RuleHit`` schema. This module owns
no decision logic of its own — it is purely a translation layer between the
domain object and the DTO, keeping the "why this risk level" narrative
strictly downstream of the policy that actually decided it.
"""

from __future__ import annotations

from app.domain.risk import RuleHitRecord
from app.schemas.prediction import RuleHit


def build_rule_hits(rule_hits: list[RuleHitRecord]) -> list[RuleHit]:
    return [
        RuleHit(
            rule_id=hit.rule_id,
            rule_name=hit.rule_name,
            condition=hit.condition,
            actual_value=hit.actual_value,
            threshold=hit.threshold,
            met=hit.met,
            weight=hit.weight,
        )
        for hit in rule_hits
    ]
