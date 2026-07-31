"""Deterministic policy for explanation-only observational graph evidence."""

from __future__ import annotations

from dataclasses import dataclass


RELATION_POLICY_VERSION = "explanation-evidence-v2"

DIAGNOSTIC_RELATION_ROLES = frozenset(
    {
        "state_persistence",
        "measurement_agreement",
        "cross_source_persistence",
        "contemporaneous_association",
    }
)


@dataclass(frozen=True)
class RelationAssessment:
    """Describe what an extracted association may and may not be used for."""

    relation_role: str
    validation_stage: str
    support_rate: float
    eligible_for_prediction_experiment: bool
    eligible_for_production_prediction: bool
    transferability_status: str
    evidence_quality_checks: dict[str, bool]


def assess_relation(
    *,
    source_concept_iri: str,
    target_concept_iri: str,
    source_phenomenon_family: str,
    target_phenomenon_family: str,
    target_is_extreme_weather: bool,
    lag_days: int,
    support_episode_count: int,
    counterexample_episode_count: int,
    lift: float,
    coverage_gate_passed: bool,
    min_support_episodes: int,
    min_lift: float,
    min_candidate_support_rate: float,
) -> RelationAssessment:
    """Classify an association without promoting it into prediction or causality."""

    if lag_days < 0:
        raise ValueError("lag_days must be non-negative")
    if support_episode_count < 0 or counterexample_episode_count < 0:
        raise ValueError("episode counts must be non-negative")
    if not 0.0 <= min_candidate_support_rate <= 1.0:
        raise ValueError("min_candidate_support_rate must be between 0 and 1")

    episode_count = support_episode_count + counterexample_episode_count
    support_rate = support_episode_count / episode_count if episode_count else 0.0
    same_state = source_concept_iri == target_concept_iri
    same_phenomenon = (
        source_phenomenon_family != "unspecified"
        and source_phenomenon_family == target_phenomenon_family
    )

    if same_state:
        relation_role = "state_persistence"
    elif same_phenomenon and lag_days == 0:
        relation_role = "measurement_agreement"
    elif same_phenomenon:
        relation_role = "cross_source_persistence"
    elif lag_days == 0:
        relation_role = "contemporaneous_association"
    else:
        relation_role = "lagged_cross_indicator"

    evidence_quality_checks = {
        "cross_indicator_lagged": relation_role == "lagged_cross_indicator",
        "targets_extreme_weather": target_is_extreme_weather,
        "coverage_gate_passed": coverage_gate_passed,
        "minimum_support_episodes_passed": (
            support_episode_count >= min_support_episodes
        ),
        "minimum_lift_passed": lift >= min_lift,
        "minimum_support_rate_passed": (
            support_rate >= min_candidate_support_rate
        ),
    }
    if relation_role in DIAGNOSTIC_RELATION_ROLES:
        validation_stage = "diagnostic_evidence"
    else:
        validation_stage = "observational_evidence"

    return RelationAssessment(
        relation_role=relation_role,
        validation_stage=validation_stage,
        support_rate=support_rate,
        eligible_for_prediction_experiment=False,
        eligible_for_production_prediction=False,
        transferability_status="not_evaluated_on_saudi",
        evidence_quality_checks=evidence_quality_checks,
    )
