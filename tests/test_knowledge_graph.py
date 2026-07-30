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
from mazu_saudi.knowledge_graph.builder import discover_indicator_files
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
    assert latest["ontology_version"] == "1.1.0"
    assert latest["scope_label"] == "synthetic-2025"
    view = store.graph_view()
    assert view["build"]["build_id"] == result.build_id
    assert any(
        node["ontology_class_iri"]
        == "urn:mazu-saudi:ontology:LaggedAssociationAssertion"
        for node in view["nodes"]
    )
    assert any(
        edge["predicate_iri"] == "urn:mazu-saudi:ontology:sourceState"
        for edge in view["edges"]
    )
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
            SELECT eligible_for_causal_explanation, lift
            FROM kg_evidence
            WHERE source_state_iri='urn:mazu-saudi:concept:HighIVTState'
              AND target_state_iri='urn:mazu-saudi:concept:ExtremeRainfallState'
              AND lag_days=1
            """
        ).fetchone()
        assert evidence is not None
        assert evidence[0] == 0
        assert evidence[1] > 1.0
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
