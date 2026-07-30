"""Auditable KnowWhereGraph geography and historical-background enrichment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


KWG_PROVIDER = "KnowWhereGraph"
KWG_DEFAULT_ENDPOINT = "https://stko-kwg.geog.ucsb.edu/sparql"
ALLOWED_KWG_HOSTS = {"stko-kwg.geog.ucsb.edu", "knowwheregraph.org"}
ALLOWED_ENTITY_KINDS = {"region", "historical_event"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _is_http_iri(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_kwg_iri(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.netloc in ALLOWED_KWG_HOSTS


@dataclass(frozen=True)
class BackgroundRunResult:
    run_id: str
    status: str
    entity_count: int
    relation_count: int
    source_snapshot_sha256: str | None
    error: str | None


class KWGBackgroundStore:
    """Persist external background separately from observational graph builds."""

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
                CREATE TABLE IF NOT EXISTS kg_external_background_runs (
                    run_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    country_iso3 TEXT NOT NULL,
                    start_time TEXT,
                    end_time TEXT,
                    query_manifest_sha256 TEXT,
                    source_snapshot_sha256 TEXT,
                    retrieved_at TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK(status IN ('successful','empty','source_unavailable')),
                    error TEXT,
                    entity_count INTEGER NOT NULL,
                    relation_count INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kg_external_background_entities (
                    run_id TEXT NOT NULL
                        REFERENCES kg_external_background_runs(run_id) ON DELETE CASCADE,
                    entity_iri TEXT NOT NULL,
                    entity_kind TEXT NOT NULL
                        CHECK(entity_kind IN ('region','historical_event')),
                    external_type_iri TEXT NOT NULL,
                    label TEXT NOT NULL,
                    start_time TEXT,
                    end_time TEXT,
                    geometry_wkt TEXT,
                    source_dataset_iri TEXT,
                    properties_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, entity_iri)
                );

                CREATE TABLE IF NOT EXISTS kg_external_background_relations (
                    relation_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL
                        REFERENCES kg_external_background_runs(run_id) ON DELETE CASCADE,
                    source_iri TEXT NOT NULL,
                    predicate_iri TEXT NOT NULL,
                    target_iri TEXT NOT NULL,
                    properties_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_external_entities_kind
                    ON kg_external_background_entities(entity_kind);
                CREATE INDEX IF NOT EXISTS idx_external_relations_source
                    ON kg_external_background_relations(source_iri);
                CREATE INDEX IF NOT EXISTS idx_external_relations_target
                    ON kg_external_background_relations(target_iri);
                """
            )

    def import_snapshot(
        self,
        snapshot: dict[str, Any],
        *,
        query_manifest_sha256: str | None = None,
    ) -> BackgroundRunResult:
        normalized = validate_kwg_snapshot(snapshot)
        entity_count = len(normalized["entities"])
        relation_count = len(normalized["relations"])
        status = "successful" if entity_count else "empty"
        run_id = f"urn:mazu-saudi:kwg-run:{uuid4()}"
        snapshot_sha = _sha256_json(normalized)
        scope = normalized["scope"]
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO kg_external_background_runs(
                    run_id, provider, endpoint, country_iso3, start_time, end_time,
                    query_manifest_sha256, source_snapshot_sha256, retrieved_at,
                    status, error, entity_count, relation_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    run_id,
                    normalized["provider"],
                    normalized["endpoint"],
                    scope["country_iso3"],
                    scope.get("start_time"),
                    scope.get("end_time"),
                    query_manifest_sha256,
                    snapshot_sha,
                    normalized["retrieved_at"],
                    status,
                    entity_count,
                    relation_count,
                ),
            )
            connection.executemany(
                """
                INSERT INTO kg_external_background_entities(
                    run_id, entity_iri, entity_kind, external_type_iri,
                    label, start_time, end_time, geometry_wkt,
                    source_dataset_iri, properties_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        entity["entity_iri"],
                        entity["entity_kind"],
                        entity["external_type_iri"],
                        entity["label"],
                        entity.get("start_time"),
                        entity.get("end_time"),
                        entity.get("geometry_wkt"),
                        entity.get("source_dataset_iri"),
                        _canonical_json(entity.get("properties", {})),
                    )
                    for entity in normalized["entities"]
                ],
            )
            connection.executemany(
                """
                INSERT INTO kg_external_background_relations(
                    relation_id, run_id, source_iri, predicate_iri,
                    target_iri, properties_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        f"{run_id}:relation:{index}",
                        run_id,
                        relation["source_iri"],
                        relation["predicate_iri"],
                        relation["target_iri"],
                        _canonical_json(relation.get("properties", {})),
                    )
                    for index, relation in enumerate(normalized["relations"], start=1)
                ],
            )
        return BackgroundRunResult(
            run_id=run_id,
            status=status,
            entity_count=entity_count,
            relation_count=relation_count,
            source_snapshot_sha256=snapshot_sha,
            error=None,
        )

    def record_source_unavailable(
        self,
        *,
        endpoint: str,
        scope: dict[str, Any],
        error: str,
        query_manifest_sha256: str | None = None,
        retrieved_at: str | None = None,
    ) -> BackgroundRunResult:
        if not _is_kwg_iri(endpoint):
            raise ValueError("KWG endpoint must use an official KWG host")
        country_iso3 = _validate_scope(scope)["country_iso3"]
        if not error.strip():
            raise ValueError("A source-unavailable run must record an error")
        retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
        _parse_timestamp(retrieved_at, "retrieved_at")
        run_id = f"urn:mazu-saudi:kwg-run:{uuid4()}"
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO kg_external_background_runs(
                    run_id, provider, endpoint, country_iso3, start_time, end_time,
                    query_manifest_sha256, source_snapshot_sha256, retrieved_at,
                    status, error, entity_count, relation_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, 'source_unavailable', ?, 0, 0)
                """,
                (
                    run_id,
                    KWG_PROVIDER,
                    endpoint,
                    country_iso3,
                    scope.get("start_time"),
                    scope.get("end_time"),
                    query_manifest_sha256,
                    retrieved_at,
                    error.strip()[:2000],
                ),
            )
        return BackgroundRunResult(
            run_id=run_id,
            status="source_unavailable",
            entity_count=0,
            relation_count=0,
            source_snapshot_sha256=None,
            error=error.strip()[:2000],
        )

    def latest_run(self) -> dict[str, Any] | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM kg_external_background_runs
                ORDER BY retrieved_at DESC, run_id DESC
                LIMIT 1
                """
            ).fetchone()
        return dict(row) if row else None

    def latest_available_run(self) -> dict[str, Any] | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM kg_external_background_runs
                WHERE status='successful' AND entity_count > 0
                ORDER BY retrieved_at DESC, run_id DESC
                LIMIT 1
                """
            ).fetchone()
        return dict(row) if row else None

    def background_view(self, run_id: str | None = None) -> dict[str, Any]:
        self.initialize()
        with self._connect() as connection:
            if run_id is None:
                run = connection.execute(
                    """
                    SELECT * FROM kg_external_background_runs
                    WHERE status='successful' AND entity_count > 0
                    ORDER BY retrieved_at DESC, run_id DESC
                    LIMIT 1
                    """
                ).fetchone()
            else:
                run = connection.execute(
                    "SELECT * FROM kg_external_background_runs WHERE run_id=?",
                    (run_id,),
                ).fetchone()
            if run is None:
                return {"run": None, "entities": [], "relations": []}
            entities = connection.execute(
                """
                SELECT * FROM kg_external_background_entities
                WHERE run_id=? ORDER BY entity_kind, entity_iri
                """,
                (run["run_id"],),
            ).fetchall()
            relations = connection.execute(
                """
                SELECT * FROM kg_external_background_relations
                WHERE run_id=? ORDER BY relation_id
                """,
                (run["run_id"],),
            ).fetchall()
        entity_values = []
        for row in entities:
            value = dict(row)
            value["properties"] = json.loads(value.pop("properties_json"))
            entity_values.append(value)
        relation_values = []
        for row in relations:
            value = dict(row)
            value["properties"] = json.loads(value.pop("properties_json"))
            relation_values.append(value)
        return {
            "run": dict(run),
            "entities": entity_values,
            "relations": relation_values,
        }


def _validate_scope(scope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scope, dict):
        raise ValueError("KWG snapshot scope must be an object")
    country_iso3 = scope.get("country_iso3", "")
    if len(country_iso3) != 3 or country_iso3 != country_iso3.upper():
        raise ValueError("KWG scope country_iso3 must be an uppercase ISO3 code")
    for field in ("start_time", "end_time"):
        if scope.get(field):
            _parse_timestamp(scope[field], f"scope.{field}")
    if scope.get("start_time") and scope.get("end_time"):
        if _parse_timestamp(scope["start_time"], "scope.start_time") > _parse_timestamp(
            scope["end_time"], "scope.end_time"
        ):
            raise ValueError("KWG scope start_time must not be after end_time")
    return scope


def validate_kwg_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Reject ungrounded or semantically unsafe external background records."""

    if snapshot.get("provider") != KWG_PROVIDER:
        raise ValueError(f"KWG snapshot provider must be {KWG_PROVIDER}")
    endpoint = snapshot.get("endpoint", "")
    if not _is_kwg_iri(endpoint):
        raise ValueError("KWG snapshot endpoint must use an official KWG host")
    _parse_timestamp(snapshot.get("retrieved_at", ""), "retrieved_at")
    scope = _validate_scope(snapshot.get("scope"))
    entities = snapshot.get("entities")
    relations = snapshot.get("relations")
    if not isinstance(entities, list) or not isinstance(relations, list):
        raise ValueError("KWG snapshot entities and relations must be arrays")

    entity_ids: set[str] = set()
    for entity in entities:
        entity_iri = entity.get("entity_iri", "")
        if not _is_kwg_iri(entity_iri):
            raise ValueError(f"External entity is not a KWG IRI: {entity_iri}")
        if entity_iri in entity_ids:
            raise ValueError(f"Duplicate KWG entity IRI: {entity_iri}")
        entity_ids.add(entity_iri)
        if entity.get("entity_kind") not in ALLOWED_ENTITY_KINDS:
            raise ValueError(f"Unsupported KWG entity kind: {entity.get('entity_kind')}")
        if not _is_http_iri(entity.get("external_type_iri", "")):
            raise ValueError(f"KWG entity lacks a valid external type: {entity_iri}")
        if not str(entity.get("label", "")).strip():
            raise ValueError(f"KWG entity lacks a label: {entity_iri}")
        if not isinstance(entity.get("properties", {}), dict):
            raise ValueError(f"KWG entity properties must be an object: {entity_iri}")
        for field in ("start_time", "end_time"):
            if entity.get(field):
                _parse_timestamp(entity[field], f"{entity_iri}.{field}")
        if entity["entity_kind"] == "region":
            if not str(entity.get("properties", {}).get("gadm_gid", "")).startswith(
                scope["country_iso3"]
            ):
                raise ValueError(
                    f"KWG region GADM identifier is outside requested country: {entity_iri}"
                )
        if entity["entity_kind"] == "historical_event":
            if not entity.get("start_time"):
                raise ValueError(f"Historical event lacks start_time: {entity_iri}")
            if not _is_http_iri(entity.get("source_dataset_iri", "")):
                raise ValueError(
                    f"Historical event lacks source_dataset_iri: {entity_iri}"
                )

    relation_ids: set[tuple[str, str, str]] = set()
    for relation in relations:
        identity = (
            relation.get("source_iri", ""),
            relation.get("predicate_iri", ""),
            relation.get("target_iri", ""),
        )
        if identity in relation_ids:
            raise ValueError(f"Duplicate KWG background relation: {identity}")
        relation_ids.add(identity)
        if identity[0] not in entity_ids or identity[2] not in entity_ids:
            raise ValueError(f"KWG background relation has an unknown endpoint: {identity}")
        if not _is_http_iri(identity[1]):
            raise ValueError(f"KWG relation predicate must be an HTTP IRI: {identity[1]}")
        if not isinstance(relation.get("properties", {}), dict):
            raise ValueError(f"KWG relation properties must be an object: {identity}")
    return {
        "provider": KWG_PROVIDER,
        "endpoint": endpoint,
        "retrieved_at": snapshot["retrieved_at"],
        "scope": scope,
        "entities": entities,
        "relations": relations,
    }


def _binding_value(binding: dict[str, Any], name: str) -> str | None:
    value = binding.get(name)
    return value.get("value") if isinstance(value, dict) else None


def snapshot_from_sparql_results(
    *,
    endpoint: str,
    scope: dict[str, Any],
    retrieved_at: str,
    geography: dict[str, Any],
    history: dict[str, Any],
) -> dict[str, Any]:
    """Normalize two bounded SPARQL result sets into the import contract."""

    entities: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []
    for row in geography.get("results", {}).get("bindings", []):
        entity_iri = _binding_value(row, "entity")
        external_type = _binding_value(row, "type")
        label = _binding_value(row, "label")
        gid = _binding_value(row, "gid")
        if not all((entity_iri, external_type, label, gid)):
            continue
        entities[entity_iri] = {
            "entity_iri": entity_iri,
            "entity_kind": "region",
            "external_type_iri": external_type,
            "label": label,
            "geometry_wkt": _binding_value(row, "geometry"),
            "properties": {"gadm_gid": gid},
        }
        parent = _binding_value(row, "parent")
        if parent:
            relations.append(
                {
                    "source_iri": entity_iri,
                    "predicate_iri": (
                        "http://stko-kwg.geog.ucsb.edu/lod/ontology/"
                        "administrativePartOf"
                    ),
                    "target_iri": parent,
                    "properties": {},
                }
            )

    for row in history.get("results", {}).get("bindings", []):
        entity_iri = _binding_value(row, "entity")
        external_type = _binding_value(row, "type")
        label = _binding_value(row, "label")
        start = _binding_value(row, "start")
        dataset = _binding_value(row, "dataset")
        region = _binding_value(row, "region")
        if not all((entity_iri, external_type, label, start, dataset, region)):
            continue
        entities[entity_iri] = {
            "entity_iri": entity_iri,
            "entity_kind": "historical_event",
            "external_type_iri": external_type,
            "label": label,
            "start_time": start,
            "end_time": _binding_value(row, "end"),
            "geometry_wkt": _binding_value(row, "geometry"),
            "source_dataset_iri": dataset,
            "properties": {},
        }
        relations.append(
            {
                "source_iri": entity_iri,
                "predicate_iri": "http://www.w3.org/ns/sosa/hasFeatureOfInterest",
                "target_iri": region,
                "properties": {"role": "historical-background-location"},
            }
        )
    relations = [
        relation
        for relation in relations
        if relation["source_iri"] in entities and relation["target_iri"] in entities
    ]
    return {
        "provider": KWG_PROVIDER,
        "endpoint": endpoint,
        "retrieved_at": retrieved_at,
        "scope": scope,
        "entities": list(entities.values()),
        "relations": relations,
    }


def query_kwg(endpoint: str, query: str, *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Execute a bounded read-only SPARQL query and return its JSON result."""

    if not _is_kwg_iri(endpoint):
        raise ValueError("KWG endpoint must use an official KWG host")
    normalized_query = " ".join(query.upper().split())
    forbidden = ("INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "CREATE", "MOVE", "COPY", "ADD")
    if "SELECT " not in normalized_query or any(
        f"{keyword} " in normalized_query for keyword in forbidden
    ):
        raise ValueError("KWG enrichment only permits SPARQL SELECT queries")
    url = f"{endpoint}?{urlencode({'query': query})}"
    request = Request(
        url,
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "MAZU-Saudi-KWG-Enrichment/1.0",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            try:
                payload = json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RuntimeError("KWG response is not valid UTF-8 JSON") from exc
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"KWG HTTP {exc.code}: {body or exc.reason}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"KWG request failed: {exc}") from exc
    if not isinstance(payload.get("results", {}).get("bindings"), list):
        raise RuntimeError("KWG response is not a SPARQL SELECT JSON result")
    return payload


def run_kwg_enrichment(
    *,
    database_file: Path,
    query_manifest_file: Path,
    endpoint: str = KWG_DEFAULT_ENDPOINT,
    country_iso3: str = "SAU",
    timeout_seconds: float = 30.0,
) -> BackgroundRunResult:
    """Run the bounded KWG query pair, recording outages without fabricated data."""

    manifest = json.loads(Path(query_manifest_file).read_text(encoding="utf-8"))
    manifest_sha = _sha256_json(manifest)
    if manifest.get("country_iso3") != country_iso3:
        raise ValueError(
            "KWG query manifest country_iso3 does not match the requested country"
        )
    scope = {"country_iso3": country_iso3}
    _validate_scope(scope)
    queries = {item["role"]: item["sparql"] for item in manifest["queries"]}
    if set(queries) != {"geography", "history"}:
        raise ValueError("KWG query manifest must define geography and history roles")
    store = KWGBackgroundStore(database_file)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    try:
        geography = query_kwg(endpoint, queries["geography"], timeout_seconds=timeout_seconds)
        history = query_kwg(endpoint, queries["history"], timeout_seconds=timeout_seconds)
    except RuntimeError as exc:
        return store.record_source_unavailable(
            endpoint=endpoint,
            scope=scope,
            error=str(exc),
            query_manifest_sha256=manifest_sha,
            retrieved_at=retrieved_at,
        )
    snapshot = snapshot_from_sparql_results(
        endpoint=endpoint,
        scope=scope,
        retrieved_at=retrieved_at,
        geography=geography,
        history=history,
    )
    return store.import_snapshot(snapshot, query_manifest_sha256=manifest_sha)


def result_as_dict(result: BackgroundRunResult) -> dict[str, Any]:
    return asdict(result)
