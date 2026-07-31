from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
import sqlite3

import numpy as np
import pytest
import xarray as xr

from mazu_saudi.knowledge_graph import (
    BuildConfig,
    KnowledgeGraphStore,
    build_statistical_knowledge_graph,
)
from mazu_saudi.knowledge_graph.builder import (
    Association,
    DEFAULT_STATE_SPECS,
    _select_associations,
    discover_indicator_files,
)
from mazu_saudi.ontology import materialize_ontology


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"


def write_indicator_days(
    root: Path,
    count: int = 36,
    *,
    missing_analysis_indices: set[int] | None = None,
) -> None:
    missing_analysis_indices = missing_analysis_indices or set()
    latitudes = np.asarray([5.0, 15.0])
    longitudes = np.asarray([5.0, 15.0])
    shape = (2, 2)
    for day_index in range(count):
        current = date(2025, 3, 1) + timedelta(days=day_index)
        phase = float(day_index % 10)
        ivt = np.full(shape, phase)
        if day_index in missing_analysis_indices:
            ivt[:] = np.nan
        rain = np.full(shape, float((day_index - 1) % 10))
        dataset = xr.Dataset(
            {
                "ivt": (("latitude", "longitude"), ivt),
                "cape": (
                    ("latitude", "longitude"),
                    np.full(
                        shape,
                        np.nan
                        if day_index in missing_analysis_indices
                        else 100.0,
                    ),
                ),
                "pwat": (
                    ("latitude", "longitude"),
                    np.full(
                        shape,
                        np.nan
                        if day_index in missing_analysis_indices
                        else 20.0,
                    ),
                ),
                "daily_precip_total": (("latitude", "longitude"), rain),
                "tmax_c": (("latitude", "longitude"), np.full(shape, 30.0)),
                "wind10_speed": (("latitude", "longitude"), np.full(shape, 5.0)),
                "vpd_kpa": (("latitude", "longitude"), np.full(shape, 1.0)),
                "satellite_precip_total": (
                    ("latitude", "longitude"),
                    rain * 1.1,
                ),
                "satellite_precip_coverage": (
                    ("latitude", "longitude"),
                    np.ones(shape),
                ),
                "sst_c": (
                    ("latitude", "longitude"),
                    np.full(shape, 25.0 + phase / 10.0),
                ),
                "monthly_precip_total": (
                    ("latitude", "longitude"),
                    np.full(shape, 60.0),
                ),
                "monthly_tmax_c": (
                    ("latitude", "longitude"),
                    np.full(shape, 35.0),
                ),
            },
            coords={"latitude": latitudes, "longitude": longitudes},
        )
        dataset.attrs["analysis_source_quality"] = (
            "missing_required_messages"
            if day_index in missing_analysis_indices
            else "complete"
        )
        dataset.to_netcdf(root / f"global_indicators_{current:%Y%m%d}.nc")


def test_complete_year_is_required_by_default(tmp_path):
    write_indicator_days(tmp_path, count=2)
    with pytest.raises(ValueError, match="complete 2025 year"):
        discover_indicator_files(tmp_path, BuildConfig())

    files = discover_indicator_files(
        tmp_path,
        replace(BuildConfig(), require_complete_year=False),
    )
    assert [day.isoformat() for day, _ in files] == ["2025-03-01", "2025-03-02"]


def test_observational_associations_use_one_quality_ranking_without_prediction_quota():
    candidate = Association(
        source_state_index=0,
        target_state_index=3,
        season="MAM",
        lag_days=1,
        opportunity_count=100,
        source_occurrence_count=30,
        target_occurrence_count=20,
        joint_occurrence_count=10,
        support_episode_indices=tuple(range(10)),
        counterexample_episode_indices=tuple(range(10, 20)),
        baseline_rate=0.2,
        conditional_rate=1 / 3,
        lift=1.67,
    )
    persistence = replace(
        candidate,
        source_state_index=6,
        target_state_index=6,
        support_episode_indices=tuple(range(40)),
        counterexample_episode_indices=tuple(range(40, 45)),
        lift=8.0,
    )

    selected = _select_associations(
        [persistence, candidate],
        state_specs=DEFAULT_STATE_SPECS,
        config=BuildConfig(
            max_assertions=1,
            min_support_episodes=8,
            min_lift=1.15,
            min_candidate_support_rate=0.25,
        ),
    )

    assert selected == [persistence]


def test_store_adds_policy_columns_without_reclassifying_legacy_builds(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE kg_evidence (
                assertion_id TEXT PRIMARY KEY,
                build_id TEXT NOT NULL,
                source_state_iri TEXT NOT NULL,
                target_state_iri TEXT NOT NULL,
                context_id TEXT NOT NULL,
                lag_days INTEGER NOT NULL,
                opportunity_count INTEGER NOT NULL,
                source_occurrence_count INTEGER NOT NULL,
                target_occurrence_count INTEGER NOT NULL,
                joint_occurrence_count INTEGER NOT NULL,
                support_episode_count INTEGER NOT NULL,
                counterexample_episode_count INTEGER NOT NULL,
                baseline_rate REAL NOT NULL,
                conditional_rate REAL NOT NULL,
                lift REAL NOT NULL,
                evidence_class TEXT NOT NULL,
                eligible_for_causal_explanation INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO kg_evidence VALUES (
                'legacy-assertion', 'legacy-build', 'urn:source', 'urn:target',
                'urn:context', 1, 10, 4, 3, 2, 2, 2, 0.3, 0.5, 1.67,
                'observational-statistical', 0
            )
            """
        )

    KnowledgeGraphStore(database).initialize()

    with sqlite3.connect(database) as connection:
        migrated = connection.execute(
            """
            SELECT relation_policy_version, relation_role, validation_stage,
                   eligible_for_prediction_experiment
            FROM kg_evidence
            """
        ).fetchone()
    assert migrated == (
        "legacy-unclassified",
        "legacy_unclassified",
        "legacy_statistical_evidence",
        0,
    )


def test_statistical_graph_is_materialized_with_ontology_conformance(tmp_path):
    indicators = tmp_path / "indicators"
    indicators.mkdir()
    write_indicator_days(indicators)
    database = tmp_path / "mazu.sqlite3"
    materialize_ontology(ONTOLOGY, database)

    result = build_statistical_knowledge_graph(
        input_dir=indicators,
        database_file=database,
        config=BuildConfig(
            require_complete_year=False,
            tile_degrees=10.0,
            min_support_episodes=2,
            min_lift=1.1,
            max_lag_days=2,
            max_assertions=20,
            evidence_episode_limit=3,
            scope_label="synthetic-2025",
        ),
    )

    assert result.input_file_count == 36
    assert result.spatial_tile_count == 4
    assert result.assertion_count > 0
    assert result.episode_count > 0
    assert result.node_count > result.assertion_count

    store = KnowledgeGraphStore(database)
    latest = store.latest_build()
    assert latest["build_id"] == result.build_id
    assert latest["ontology_version"] == "2.0.0"
    assert latest["scope_label"] == "synthetic-2025"
    view = store.graph_view()
    assert view["build"]["build_id"] == result.build_id
    assert any(
        node["ontology_class_iri"]
        == "urn:mazu-saudi:ontology:LaggedAssociationAssertion"
        for node in view["nodes"]
    )
    assertion_nodes = [
        node
        for node in view["nodes"]
        if node["ontology_class_iri"]
        == "urn:mazu-saudi:ontology:LaggedAssociationAssertion"
    ]
    assert all(
        node["properties"]["coverage_gate_passed"]
        and not node["properties"]["eligible_for_production_prediction"]
        and not node["properties"]["eligible_for_causal_explanation"]
        for node in assertion_nodes
    )
    assert all(
        not node["properties"]["eligible_for_prediction_experiment"]
        for node in assertion_nodes
    )
    assert {
        node["properties"]["validation_stage"] for node in assertion_nodes
    } <= {
        "diagnostic_evidence",
        "observational_evidence",
    }
    assert any(
        node["properties"]["relation_role"] == "measurement_agreement"
        for node in assertion_nodes
    )
    assert result.observational_assertion_count == sum(
        node["properties"]["validation_stage"] == "observational_evidence"
        for node in assertion_nodes
    )
    assert {node["properties"]["evidence_layer"] for node in assertion_nodes} <= {
        "observable",
        "dynamic",
        "mixed",
    }
    assert any(
        edge["predicate_iri"] == "urn:mazu-saudi:ontology:sourceState"
        for edge in view["edges"]
    )
    extreme_state_ids = {
        node["node_id"]
        for node in view["nodes"]
        if node["ontology_class_iri"]
        == "urn:mazu-saudi:ontology:ExtremeWeatherState"
        and not node["node_id"].startswith("urn:mazu-saudi:concept:")
    }
    indicator_derived_state_ids = {
        edge["source_id"]
        for edge in view["edges"]
        if edge["predicate_iri"]
        == "urn:mazu-saudi:ontology:derivedFromIndicator"
    }
    assert extreme_state_ids
    assert extreme_state_ids <= indicator_derived_state_ids
    assert any(
        edge["predicate_iri"] == "http://www.w3.org/ns/prov#used"
        and edge["target_id"]
        == "urn:mazu-saudi:concept:FYMERGSatellitePrecipitationProduct"
        for edge in view["edges"]
    )
    assert any(
        "sst_c" in node["properties"].get("multi_source_context", {})
        and "data_availability"
        in node["properties"].get("multi_source_context", {})
        for node in view["nodes"]
        if node["ontology_class_iri"] == "urn:mazu-saudi:ontology:WeatherEpisode"
    )

    with sqlite3.connect(database) as connection:
        evidence = connection.execute(
            """
            SELECT eligible_for_causal_explanation, lift, relation_role,
                   validation_stage, eligible_for_prediction_experiment,
                   transferability_status
            FROM kg_evidence
            WHERE source_state_iri='urn:mazu-saudi:concept:HighIVTState'
              AND target_state_iri='urn:mazu-saudi:concept:ExtremeRainfallState'
              AND lag_days=1
            """
        ).fetchone()
        assert evidence is not None
        assert evidence[0] == 0
        assert evidence[1] > 1.0
        assert evidence[2] == "lagged_cross_indicator"
        assert evidence[3] == "observational_evidence"
        assert evidence[4] == 0
        assert evidence[5] == "not_evaluated_on_saudi"
        assert connection.execute("SELECT COUNT(*) FROM kg_thresholds").fetchone()[0] > 0

    # Ontology rematerialization only replaces ontology tables; graph builds stay immutable.
    materialize_ontology(ONTOLOGY, database)
    assert KnowledgeGraphStore(database).latest_build()["build_id"] == result.build_id


def test_builder_rejects_indicator_files_that_do_not_match_the_contract(tmp_path):
    indicators = tmp_path / "indicators"
    indicators.mkdir()
    xr.Dataset(
        {"ivt": (("latitude", "longitude"), np.ones((1, 1)))},
        coords={"latitude": [0.0], "longitude": [0.0]},
    ).to_netcdf(indicators / "global_indicators_20250301.nc")
    database = tmp_path / "mazu.sqlite3"
    materialize_ontology(ONTOLOGY, database)

    with pytest.raises(ValueError, match="absent from every input file"):
        build_statistical_knowledge_graph(
            input_dir=indicators,
            database_file=database,
            config=BuildConfig(require_complete_year=False),
        )


def test_formal_graph_rejects_seasonal_gaps_but_validation_graph_records_them(
    tmp_path,
):
    indicators = tmp_path / "indicators"
    indicators.mkdir()
    write_indicator_days(
        indicators,
        count=20,
        missing_analysis_indices=set(range(10)),
    )
    database = tmp_path / "mazu.sqlite3"
    materialize_ontology(ONTOLOGY, database)
    base = BuildConfig(
        require_complete_year=False,
        min_indicator_file_coverage=0.50,
        min_indicator_season_coverage=0.75,
        min_support_episodes=1,
    )

    with pytest.raises(ValueError, match="seasonal file coverage"):
        build_statistical_knowledge_graph(
            input_dir=indicators,
            database_file=database,
            config=base,
        )

    result = build_statistical_knowledge_graph(
        input_dir=indicators,
        database_file=database,
        config=replace(
            base,
            allow_degraded_coverage=True,
            scope_label="synthetic-validation-degraded",
        ),
    )

    latest = KnowledgeGraphStore(database).latest_build()
    assert result.input_file_count == 20
    assert latest["config"]["quality_tier"] == "validation-degraded"
    assert latest["config"]["seasonal_coverage_issues"]["ivt"]["MAM"] == 0.5
    view = KnowledgeGraphStore(database).graph_view()
    run = next(
        node
        for node in view["nodes"]
        if node["ontology_class_iri"]
        == "urn:mazu-saudi:ontology:ExtractionRun"
    )
    assert run["properties"]["quality_tier"] == "validation-degraded"
    assert run["properties"]["source_quality_counts"] == {
        "complete": 10,
        "missing_required_messages": 10,
    }
    assert (
        latest["config"]["state_season_coverage"]["high_ivt"]["MAM"][
            "coverage_gate_passed"
        ]
        is False
    )
    assert (
        latest["config"]["state_season_coverage"]["extreme_rainfall"]["MAM"][
            "coverage_gate_passed"
        ]
        is True
    )
    assertions = [
        node
        for node in view["nodes"]
        if node["ontology_class_iri"]
        == "urn:mazu-saudi:ontology:LaggedAssociationAssertion"
    ]
    assert assertions
    assert {node["properties"]["evidence_layer"] for node in assertions} == {
        "observable"
    }
    context = next(
        node
        for node in view["nodes"]
        if node["ontology_class_iri"]
        == "urn:mazu-saudi:ontology:SeasonalContext"
        and node["properties"]["season"] == "MAM"
    )
    assert "high_ivt" in context["properties"]["suppressed_relation_states"]
    assert "extreme_rainfall" in context["properties"]["available_relation_states"]


def test_degraded_coverage_requires_an_explicit_validation_scope(tmp_path):
    with pytest.raises(ValueError, match="validation-degraded"):
        build_statistical_knowledge_graph(
            input_dir=tmp_path,
            database_file=tmp_path / "mazu.sqlite3",
            config=BuildConfig(
                require_complete_year=False,
                allow_degraded_coverage=True,
                scope_label="formal-looking-scope",
            ),
        )


@pytest.mark.parametrize("coverage", [0.0, -0.1, 1.1])
def test_builder_rejects_invalid_indicator_file_coverage(tmp_path, coverage):
    with pytest.raises(ValueError, match="min_indicator_file_coverage"):
        build_statistical_knowledge_graph(
            input_dir=tmp_path,
            database_file=tmp_path / "mazu.sqlite3",
            config=BuildConfig(
                require_complete_year=False,
                min_indicator_file_coverage=coverage,
            ),
        )
