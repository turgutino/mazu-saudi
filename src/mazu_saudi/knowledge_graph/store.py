"""SQLite persistence for ontology-conformant knowledge-graph instances."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
OWL_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty"
PROV_WAS_GENERATED_BY = "http://www.w3.org/ns/prov#wasGeneratedBy"


def _json(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class KnowledgeGraphStore:
    """Persist immutable graph builds beside, but separate from, ontology tables."""

    def __init__(self, database_file: Path):
        self.database_file = Path(database_file)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_file)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS kg_builds (
                    build_id TEXT PRIMARY KEY,
                    ontology_iri TEXT NOT NULL,
                    ontology_version TEXT NOT NULL,
                    ontology_sha256 TEXT NOT NULL,
                    input_root TEXT NOT NULL,
                    input_manifest_sha256 TEXT NOT NULL,
                    scope_label TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    file_count INTEGER NOT NULL,
                    config_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    node_count INTEGER NOT NULL,
                    edge_count INTEGER NOT NULL,
                    assertion_count INTEGER NOT NULL,
                    episode_count INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kg_nodes (
                    node_id TEXT PRIMARY KEY,
                    build_id TEXT NOT NULL REFERENCES kg_builds(build_id) ON DELETE CASCADE,
                    ontology_class_iri TEXT NOT NULL,
                    concept_iri TEXT,
                    label TEXT NOT NULL,
                    spatial_key TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    properties_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kg_edges (
                    edge_id TEXT PRIMARY KEY,
                    build_id TEXT NOT NULL REFERENCES kg_builds(build_id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL,
                    predicate_iri TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    properties_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kg_evidence (
                    assertion_id TEXT PRIMARY KEY REFERENCES kg_nodes(node_id) ON DELETE CASCADE,
                    build_id TEXT NOT NULL REFERENCES kg_builds(build_id) ON DELETE CASCADE,
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
                    support_rate REAL NOT NULL,
                    evidence_class TEXT NOT NULL,
                    relation_policy_version TEXT NOT NULL,
                    relation_role TEXT NOT NULL,
                    validation_stage TEXT NOT NULL,
                    transferability_status TEXT NOT NULL,
                    eligible_for_prediction_experiment INTEGER NOT NULL
                        CHECK(eligible_for_prediction_experiment IN (0, 1)),
                    eligible_for_production_prediction INTEGER NOT NULL
                        CHECK(eligible_for_production_prediction IN (0, 1)),
                    eligible_for_causal_explanation INTEGER NOT NULL
                        CHECK(eligible_for_causal_explanation IN (0, 1))
                );

                CREATE TABLE IF NOT EXISTS kg_thresholds (
                    build_id TEXT NOT NULL REFERENCES kg_builds(build_id) ON DELETE CASCADE,
                    context_id TEXT NOT NULL,
                    spatial_key TEXT NOT NULL,
                    state_concept_iri TEXT NOT NULL,
                    indicator_name TEXT NOT NULL,
                    quantile REAL NOT NULL,
                    threshold_value REAL,
                    sample_count INTEGER NOT NULL,
                    PRIMARY KEY (
                        build_id, context_id, spatial_key,
                        state_concept_iri, indicator_name
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_kg_nodes_build
                    ON kg_nodes(build_id);
                CREATE INDEX IF NOT EXISTS idx_kg_nodes_class
                    ON kg_nodes(ontology_class_iri);
                CREATE INDEX IF NOT EXISTS idx_kg_edges_build
                    ON kg_edges(build_id);
                CREATE INDEX IF NOT EXISTS idx_kg_edges_source
                    ON kg_edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_kg_edges_target
                    ON kg_edges(target_id);
                CREATE INDEX IF NOT EXISTS idx_kg_evidence_states
                    ON kg_evidence(source_state_iri, target_state_iri);
                """
            )
            self._ensure_evidence_columns(connection)

    @staticmethod
    def _ensure_evidence_columns(connection: sqlite3.Connection) -> None:
        """Add policy columns without rewriting immutable legacy graph builds."""

        existing = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(kg_evidence)")
        }
        additions = {
            "support_rate": "REAL NOT NULL DEFAULT 0.0",
            "relation_policy_version": (
                "TEXT NOT NULL DEFAULT 'legacy-unclassified'"
            ),
            "relation_role": "TEXT NOT NULL DEFAULT 'legacy_unclassified'",
            "validation_stage": (
                "TEXT NOT NULL DEFAULT 'legacy_statistical_evidence'"
            ),
            "transferability_status": (
                "TEXT NOT NULL DEFAULT 'not_evaluated_on_saudi'"
            ),
            "eligible_for_prediction_experiment": (
                "INTEGER NOT NULL DEFAULT 0 "
                "CHECK(eligible_for_prediction_experiment IN (0, 1))"
            ),
            "eligible_for_production_prediction": (
                "INTEGER NOT NULL DEFAULT 0 "
                "CHECK(eligible_for_production_prediction IN (0, 1))"
            ),
        }
        for column, declaration in additions.items():
            if column not in existing:
                connection.execute(
                    f"ALTER TABLE kg_evidence ADD COLUMN {column} {declaration}"
                )

    def ontology_identity(self) -> dict[str, str]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT ontology_iri, version, source_sha256
                FROM ontology_documents
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("Ontology must be materialized before building the knowledge graph")
        return dict(row)

    def build_matches_current_ontology(self, build: dict[str, Any]) -> bool:
        """Return whether a frozen graph build matches the materialized ontology."""

        ontology = self.ontology_identity()
        return (
            build.get("ontology_iri") == ontology["ontology_iri"]
            and build.get("ontology_version") == ontology["version"]
            and build.get("ontology_sha256") == ontology["source_sha256"]
        )

    def validate_ontology_resources(self, iris: Iterable[str]) -> None:
        required = sorted(set(iris))
        if not required:
            return
        found = self._ontology_resource_types(required)
        missing = [iri for iri in required if iri not in found]
        if missing:
            raise ValueError(f"Knowledge graph references resources absent from ontology: {missing}")

    def _ontology_resource_types(self, iris: Iterable[str]) -> dict[str, str]:
        required = sorted(set(iris))
        if not required:
            return {}
        placeholders = ",".join("?" for _ in required)
        with self._connect() as connection:
            return {
                row["iri"]: row["resource_type"]
                for row in connection.execute(
                    f"SELECT iri, resource_type FROM resources WHERE iri IN ({placeholders})",
                    required,
                )
            }

    def _validate_graph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> None:
        node_ids = {node["node_id"] for node in nodes}
        if len(node_ids) != len(nodes):
            raise ValueError("Knowledge graph node IDs must be unique")
        edge_ids = {edge["edge_id"] for edge in edges}
        if len(edge_ids) != len(edges):
            raise ValueError("Knowledge graph edge IDs must be unique")

        local_resources = {
            node["ontology_class_iri"] for node in nodes
        } | {
            node["concept_iri"] for node in nodes if node.get("concept_iri")
        } | {
            edge["predicate_iri"]
            for edge in edges
            if edge["predicate_iri"].startswith("urn:mazu-saudi:")
        } | {
            endpoint
            for edge in edges
            for endpoint in (edge["source_id"], edge["target_id"])
            if endpoint.startswith("urn:mazu-saudi:concept:")
        }
        self.validate_ontology_resources(local_resources)
        resource_types = self._ontology_resource_types(local_resources)
        for node in nodes:
            if resource_types[node["ontology_class_iri"]] != OWL_CLASS:
                raise ValueError(
                    f"Graph node class is not an OWL class: {node['ontology_class_iri']}"
                )
            concept_iri = node.get("concept_iri")
            if (
                concept_iri
                and resource_types[concept_iri] != node["ontology_class_iri"]
            ):
                raise ValueError(
                    f"Concept {concept_iri} is not typed as {node['ontology_class_iri']}"
                )
        for edge in edges:
            predicate = edge["predicate_iri"]
            if (
                predicate.startswith("urn:mazu-saudi:")
                and resource_types[predicate] != OWL_OBJECT_PROPERTY
            ):
                raise ValueError(f"Graph edge predicate is not an object property: {predicate}")

        external_endpoints = {
            endpoint
            for edge in edges
            for endpoint in (edge["source_id"], edge["target_id"])
            if endpoint not in node_ids and not endpoint.startswith("urn:mazu-saudi:concept:")
        }
        if external_endpoints:
            raise ValueError(f"Graph edges reference unknown endpoints: {sorted(external_endpoints)}")

        assertion_ids = {row["assertion_id"] for row in evidence}
        if not assertion_ids.issubset(node_ids):
            raise ValueError("Every evidence row must reference a graph assertion node")
        if any(row["eligible_for_causal_explanation"] for row in evidence):
            raise ValueError("Automatically extracted assertions cannot be causal explanations")
        if any(row["eligible_for_production_prediction"] for row in evidence):
            raise ValueError(
                "Automatically extracted assertions cannot be production prediction rules"
            )
        if any(
            row["eligible_for_prediction_experiment"]
            and row["validation_stage"] != "candidate_for_saudi_evaluation"
            for row in evidence
        ):
            raise ValueError(
                "Prediction-experiment eligibility requires the Saudi evaluation stage"
            )

        required_predicates = {
            "urn:mazu-saudi:ontology:sourceState",
            "urn:mazu-saudi:ontology:targetState",
            "urn:mazu-saudi:ontology:applicableUnder",
            PROV_WAS_GENERATED_BY,
        }
        predicates_by_source: dict[str, set[str]] = {}
        for edge in edges:
            predicates_by_source.setdefault(edge["source_id"], set()).add(edge["predicate_iri"])
        for assertion_id in assertion_ids:
            missing = required_predicates - predicates_by_source.get(assertion_id, set())
            if missing:
                raise ValueError(
                    f"Assertion {assertion_id} misses required ontology predicates: {sorted(missing)}"
                )

    def write_build(
        self,
        *,
        build: dict[str, Any],
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        thresholds: list[dict[str, Any]],
    ) -> None:
        self.initialize()
        self._validate_graph(nodes, edges, evidence)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO kg_builds(
                    build_id, ontology_iri, ontology_version, ontology_sha256,
                    input_root, input_manifest_sha256, scope_label,
                    start_date, end_date, file_count, config_json, created_at,
                    node_count, edge_count, assertion_count, episode_count
                ) VALUES (
                    :build_id, :ontology_iri, :ontology_version, :ontology_sha256,
                    :input_root, :input_manifest_sha256, :scope_label,
                    :start_date, :end_date, :file_count, :config_json, :created_at,
                    :node_count, :edge_count, :assertion_count, :episode_count
                )
                """,
                {**build, "config_json": _json(build["config"])},
            )
            connection.executemany(
                """
                INSERT INTO kg_nodes(
                    node_id, build_id, ontology_class_iri, concept_iri,
                    label, spatial_key, start_time, end_time, properties_json
                ) VALUES (
                    :node_id, :build_id, :ontology_class_iri, :concept_iri,
                    :label, :spatial_key, :start_time, :end_time, :properties_json
                )
                """,
                [{**row, "properties_json": _json(row.get("properties", {}))} for row in nodes],
            )
            connection.executemany(
                """
                INSERT INTO kg_edges(
                    edge_id, build_id, source_id, predicate_iri,
                    target_id, properties_json
                ) VALUES (
                    :edge_id, :build_id, :source_id, :predicate_iri,
                    :target_id, :properties_json
                )
                """,
                [{**row, "properties_json": _json(row.get("properties", {}))} for row in edges],
            )
            connection.executemany(
                """
                INSERT INTO kg_evidence(
                    assertion_id, build_id, source_state_iri, target_state_iri,
                    context_id, lag_days, opportunity_count,
                    source_occurrence_count, target_occurrence_count,
                    joint_occurrence_count, support_episode_count,
                    counterexample_episode_count, baseline_rate,
                    conditional_rate, lift, evidence_class,
                    support_rate, relation_policy_version, relation_role,
                    validation_stage, transferability_status,
                    eligible_for_prediction_experiment,
                    eligible_for_production_prediction,
                    eligible_for_causal_explanation
                ) VALUES (
                    :assertion_id, :build_id, :source_state_iri, :target_state_iri,
                    :context_id, :lag_days, :opportunity_count,
                    :source_occurrence_count, :target_occurrence_count,
                    :joint_occurrence_count, :support_episode_count,
                    :counterexample_episode_count, :baseline_rate,
                    :conditional_rate, :lift, :evidence_class,
                    :support_rate, :relation_policy_version, :relation_role,
                    :validation_stage, :transferability_status,
                    :eligible_for_prediction_experiment,
                    :eligible_for_production_prediction,
                    :eligible_for_causal_explanation
                )
                """,
                evidence,
            )
            connection.executemany(
                """
                INSERT INTO kg_thresholds(
                    build_id, context_id, spatial_key, state_concept_iri,
                    indicator_name, quantile, threshold_value, sample_count
                ) VALUES (
                    :build_id, :context_id, :spatial_key, :state_concept_iri,
                    :indicator_name, :quantile, :threshold_value, :sample_count
                )
                """,
                thresholds,
            )

    def latest_build(self) -> dict[str, Any] | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM kg_builds ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["config"] = json.loads(result.pop("config_json"))
        return result

    def graph_view(self, build_id: str | None = None, *, limit: int = 500) -> dict[str, Any]:
        self.initialize()
        build = self.latest_build() if build_id is None else self._build(build_id)
        if build is None:
            return {"build": None, "nodes": [], "edges": [], "node_count": 0, "edge_count": 0}
        if not self.build_matches_current_ontology(build):
            return {
                "build": build,
                "status": "ontology_mismatch",
                "compatibility": {
                    "compatible": False,
                    "required_action": (
                        "Rebuild the observational graph with the current ontology."
                    ),
                },
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
            }
        with self._connect() as connection:
            node_rows = connection.execute(
                """
                SELECT * FROM kg_nodes
                WHERE build_id=?
                ORDER BY
                    CASE ontology_class_iri
                        WHEN 'urn:mazu-saudi:ontology:LaggedAssociationAssertion' THEN 0
                        WHEN 'urn:mazu-saudi:ontology:SeasonalContext' THEN 1
                        ELSE 2
                    END,
                    node_id
                LIMIT ?
                """,
                (build["build_id"], limit),
            ).fetchall()
            nodes = [dict(row) for row in node_rows]
            base_edge_rows = connection.execute(
                "SELECT * FROM kg_edges WHERE build_id=? ORDER BY edge_id",
                (build["build_id"],),
            ).fetchall()
            literature_run, literature_nodes, literature_edges = (
                self._literature_projection(connection, build["build_id"])
            )
        for node in nodes:
            node["properties"] = json.loads(node.pop("properties_json"))
        nodes.extend(literature_nodes)
        edges = [
            {**dict(row), "properties": json.loads(row["properties_json"])}
            for row in base_edge_rows
        ]
        for edge in edges:
            edge.pop("properties_json", None)
        edges.extend(literature_edges)
        concept_iris = {
            endpoint
            for edge in edges
            for endpoint in (edge["source_id"], edge["target_id"])
            if endpoint.startswith("urn:mazu-saudi:concept:")
        }
        if concept_iris:
            placeholders = ",".join("?" for _ in concept_iris)
            with self._connect() as connection:
                concepts = connection.execute(
                    f"""
                    SELECT iri, resource_type, local_name, label_en, label_zh
                    FROM resources
                    WHERE iri IN ({placeholders})
                    ORDER BY iri
                    """,
                    sorted(concept_iris),
                ).fetchall()
            for concept in concepts:
                nodes.append(
                    {
                        "node_id": concept["iri"],
                        "build_id": build["build_id"],
                        "ontology_class_iri": concept["resource_type"],
                        "concept_iri": concept["iri"],
                        "label": concept["label_zh"] or concept["label_en"] or concept["local_name"],
                        "spatial_key": None,
                        "start_time": None,
                        "end_time": None,
                        "properties": {
                            "kind": "ontology-concept",
                            "label_en": concept["label_en"],
                            "label_zh": concept["label_zh"],
                        },
                    }
                )
        node_ids = {node["node_id"] for node in nodes}
        edges = [
            edge
            for edge in edges
            if edge["source_id"] in node_ids and edge["target_id"] in node_ids
        ]
        return {
            "build": build,
            "literature_run": literature_run,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    @staticmethod
    def _literature_projection(
        connection: sqlite3.Connection,
        build_id: str,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ("
                "'kg_literature_runs','kg_literature_nodes',"
                "'kg_literature_edges')"
            )
        }
        if tables != {
            "kg_literature_runs",
            "kg_literature_nodes",
            "kg_literature_edges",
        }:
            return None, [], []
        run_row = connection.execute(
            """
            SELECT * FROM kg_literature_runs
            WHERE build_id=?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (build_id,),
        ).fetchone()
        if run_row is None:
            return None, [], []
        run = dict(run_row)
        run["config"] = json.loads(run.pop("config_json"))
        node_rows = connection.execute(
            """
            SELECT * FROM kg_literature_nodes
            WHERE run_id=?
            ORDER BY node_id
            """,
            (run["run_id"],),
        ).fetchall()
        nodes = []
        for row in node_rows:
            node = dict(row)
            node["properties"] = json.loads(node.pop("properties_json"))
            node.pop("run_id", None)
            node.update(
                {
                    "spatial_key": None,
                    "start_time": None,
                    "end_time": None,
                }
            )
            nodes.append(node)
        edge_rows = connection.execute(
            """
            SELECT * FROM kg_literature_edges
            WHERE run_id=?
            ORDER BY edge_id
            """,
            (run["run_id"],),
        ).fetchall()
        edges = []
        for row in edge_rows:
            edge = dict(row)
            edge["properties"] = json.loads(edge.pop("properties_json"))
            edge.pop("run_id", None)
            edges.append(edge)
        return run, nodes, edges

    def _build(self, build_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM kg_builds WHERE build_id=?",
                (build_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["config"] = json.loads(result.pop("config_json"))
        return result
