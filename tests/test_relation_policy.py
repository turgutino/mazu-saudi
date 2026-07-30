import pytest

from mazu_saudi.knowledge_graph.relation_policy import assess_relation


def assess(**overrides):
    values = {
        "source_concept_iri": "urn:source",
        "target_concept_iri": "urn:target",
        "source_phenomenon_family": "moisture_transport",
        "target_phenomenon_family": "precipitation",
        "target_is_extreme_weather": True,
        "lag_days": 1,
        "support_episode_count": 30,
        "counterexample_episode_count": 70,
        "lift": 1.8,
        "coverage_gate_passed": True,
        "min_support_episodes": 8,
        "min_lift": 1.15,
        "min_candidate_support_rate": 0.25,
    }
    values.update(overrides)
    return assess_relation(**values)


def test_cross_indicator_lagged_hazard_relation_is_only_an_evaluation_candidate():
    result = assess()

    assert result.relation_role == "lagged_cross_indicator"
    assert result.validation_stage == "candidate_for_saudi_evaluation"
    assert result.eligible_for_prediction_experiment is True
    assert result.eligible_for_production_prediction is False
    assert result.transferability_status == "not_evaluated_on_saudi"


@pytest.mark.parametrize(
    ("overrides", "expected_role"),
    [
        (
            {"target_concept_iri": "urn:source"},
            "state_persistence",
        ),
        (
            {
                "source_phenomenon_family": "precipitation",
                "target_phenomenon_family": "precipitation",
                "lag_days": 0,
            },
            "measurement_agreement",
        ),
        (
            {
                "source_phenomenon_family": "precipitation",
                "target_phenomenon_family": "precipitation",
            },
            "cross_source_persistence",
        ),
        (
            {"lag_days": 0},
            "contemporaneous_association",
        ),
    ],
)
def test_diagnostic_relations_are_preserved_but_not_prediction_candidates(
    overrides,
    expected_role,
):
    result = assess(**overrides)

    assert result.relation_role == expected_role
    assert result.validation_stage == "diagnostic_evidence"
    assert result.eligible_for_prediction_experiment is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"target_is_extreme_weather": False},
        {"support_episode_count": 20, "counterexample_episode_count": 80},
        {"coverage_gate_passed": False},
        {"lift": 1.0},
    ],
)
def test_unqualified_lagged_relation_remains_statistical_evidence(overrides):
    result = assess(**overrides)

    assert result.relation_role == "lagged_cross_indicator"
    assert result.validation_stage == "statistical_evidence"
    assert result.eligible_for_prediction_experiment is False


def test_unspecified_families_are_not_assumed_to_measure_the_same_phenomenon():
    result = assess(
        source_phenomenon_family="unspecified",
        target_phenomenon_family="unspecified",
        lag_days=0,
    )

    assert result.relation_role == "contemporaneous_association"
