"""Materialize the MAZU JSON-LD ontology into a queryable SQLite store."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
OWL_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty"
OWL_DATATYPE_PROPERTY = "http://www.w3.org/2002/07/owl#DatatypeProperty"
XSD = "http://www.w3.org/2001/XMLSchema#"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _prefixes(context: dict[str, Any]) -> dict[str, str]:
    return {
        key: value
        for key, value in context.items()
        if isinstance(value, str) and (value.startswith("http") or value.startswith("urn:"))
    }


def _expand(value: str, context: dict[str, Any]) -> str:
    if value.startswith(("http://", "https://", "urn:")):
        return value
    if ":" in value:
        prefix, suffix = value.split(":", 1)
        namespace = _prefixes(context).get(prefix)
        return f"{namespace}{suffix}" if namespace else value
    vocabulary = context.get("@vocab")
    return f"{vocabulary}{value}" if isinstance(vocabulary, str) else value


def _predicate(term: str, context: dict[str, Any]) -> str:
    if term == "@type":
        return RDF_TYPE
    definition = context.get(term)
    if isinstance(definition, dict):
        return _expand(definition["@id"], context)
    if isinstance(definition, str):
        return _expand(definition, context)
    return _expand(term, context)


def _is_iri_value(term: str, context: dict[str, Any]) -> bool:
    if term == "@type":
        return True
    definition = context.get(term)
    return isinstance(definition, dict) and definition.get("@type") == "@id"


def _literal_metadata(term: str, value: Any, context: dict[str, Any]) -> tuple[str | None, str | None]:
    definition = context.get(term)
    if isinstance(definition, dict) and definition.get("@language"):
        return definition["@language"], None
    if isinstance(value, bool):
        return None, f"{XSD}boolean"
    if isinstance(value, int):
        return None, f"{XSD}integer"
    if isinstance(value, float):
        return None, f"{XSD}decimal"
    return None, None


def _local_name(iri: str) -> str:
    for separator in ("#", "/", ":"):
        if separator in iri:
            iri = iri.rsplit(separator, 1)[-1]
    return iri


def _resource_kind(type_iris: list[str]) -> str:
    for preferred in (OWL_CLASS, OWL_OBJECT_PROPERTY, OWL_DATATYPE_PROPERTY):
        if preferred in type_iris:
            return preferred
    return type_iris[0] if type_iris else ""


class OntologyStore:
    """Read-only query interface over a materialized ontology database."""

    def __init__(self, database_file: Path):
        self.database_file = Path(database_file)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_file)
        connection.row_factory = sqlite3.Row
        return connection

    def summary(self) -> dict[str, Any]:
        with self._connect() as connection:
            document = connection.execute(
                "SELECT ontology_iri, version, source_sha256, loaded_at FROM ontology_documents"
            ).fetchone()
            resource_count = connection.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
            statement_count = connection.execute("SELECT COUNT(*) FROM statements").fetchone()[0]
            modules = {
                row["module"]: row["count"]
                for row in connection.execute(
                    """
                    SELECT module, COUNT(*) AS count
                    FROM resources
                    WHERE module IS NOT NULL
                    GROUP BY module
                    ORDER BY module
                    """
                )
            }
        return {
            "ontology": dict(document) if document else None,
            "resource_count": resource_count,
            "statement_count": statement_count,
            "modules": modules,
        }

    def get_resource(self, iri: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM resources WHERE iri=?", (iri,)).fetchone()
        return dict(row) if row else None

    def list_resources(
        self,
        *,
        module: str | None = None,
        resource_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[str] = []
        if module is not None:
            clauses.append("module=?")
            parameters.append(module)
        if resource_type is not None:
            clauses.append("resource_type=?")
            parameters.append(resource_type)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM resources{where} ORDER BY iri",
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def statements_for(self, iri: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM statements
                WHERE subject_iri=? OR (object_kind='iri' AND object_value=?)
                ORDER BY subject_iri, predicate_iri, object_value
                """,
                (iri, iri),
            ).fetchall()
        return [dict(row) for row in rows]


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS ontology_documents (
            ontology_iri TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            source_path TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS namespaces (
            prefix TEXT PRIMARY KEY,
            namespace_iri TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS resources (
            iri TEXT PRIMARY KEY,
            local_name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            module TEXT,
            status TEXT,
            label_en TEXT,
            label_zh TEXT,
            definition_en TEXT,
            definition_zh TEXT
        );
        CREATE TABLE IF NOT EXISTS statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_iri TEXT NOT NULL,
            predicate_iri TEXT NOT NULL,
            object_value TEXT NOT NULL,
            object_kind TEXT NOT NULL CHECK(object_kind IN ('iri', 'literal')),
            language TEXT,
            datatype_iri TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_statement_unique
            ON statements(
                subject_iri,
                predicate_iri,
                object_value,
                object_kind,
                IFNULL(language, ''),
                IFNULL(datatype_iri, '')
            );
        CREATE INDEX IF NOT EXISTS idx_statements_subject
            ON statements(subject_iri);
        CREATE INDEX IF NOT EXISTS idx_statements_object
            ON statements(object_value);
        CREATE INDEX IF NOT EXISTS idx_resources_module
            ON resources(module);
        """
    )


def _iter_documents(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield {key: value for key, value in payload.items() if key not in {"@context", "@graph"}}
    yield from payload.get("@graph", [])


def materialize_ontology(source_file: Path, database_file: Path) -> dict[str, Any]:
    """Validate and atomically replace the SQLite materialization."""

    source_file = Path(source_file)
    database_file = Path(database_file)
    raw = source_file.read_bytes()
    payload = json.loads(raw)
    context = payload.get("@context")
    graph = payload.get("@graph")
    if not isinstance(context, dict) or not isinstance(graph, list):
        raise ValueError("ontology source must contain object @context and list @graph")
    if not payload.get("@id") or payload.get("@type") != "owl:Ontology":
        raise ValueError("ontology source must declare one owl:Ontology document")

    subjects: set[str] = set()
    statement_rows: list[tuple[str, str, str, str, str | None, str | None]] = []
    resource_rows: list[tuple[str, str, str, str | None, str | None, str | None, str | None, str | None, str | None]] = []

    for document in _iter_documents(payload):
        raw_subject = document.get("@id")
        if not isinstance(raw_subject, str):
            raise ValueError("every ontology resource must have a string @id")
        subject = _expand(raw_subject, context)
        if subject in subjects:
            raise ValueError(f"duplicate ontology resource: {subject}")
        subjects.add(subject)

        type_values = [_expand(value, context) for value in _as_list(document.get("@type", []))]
        labels: dict[str, str] = {}
        definitions: dict[str, str] = {}
        module = document.get("module")
        status = document.get("status")

        for term, raw_value in document.items():
            if term == "@id":
                continue
            predicate = _predicate(term, context)
            for value in _as_list(raw_value):
                language: str | None = None
                datatype: str | None = None
                if isinstance(value, dict):
                    if "@id" in value:
                        object_value = _expand(value["@id"], context)
                        object_kind = "iri"
                    elif "@value" in value:
                        object_value = str(value["@value"])
                        object_kind = "literal"
                        language = value.get("@language")
                        datatype = _expand(value["@type"], context) if value.get("@type") else None
                    else:
                        raise ValueError(f"unsupported JSON-LD value on {subject}: {value}")
                elif _is_iri_value(term, context):
                    object_value = _expand(str(value), context)
                    object_kind = "iri"
                else:
                    object_value = str(value).lower() if isinstance(value, bool) else str(value)
                    object_kind = "literal"
                    language, datatype = _literal_metadata(term, value, context)
                statement_rows.append(
                    (subject, predicate, object_value, object_kind, language, datatype)
                )
                if predicate == "http://www.w3.org/2004/02/skos/core#prefLabel" and language:
                    labels[language] = object_value
                if predicate == "http://www.w3.org/2004/02/skos/core#definition" and language:
                    definitions[language] = object_value

        resource_rows.append(
            (
                subject,
                _local_name(subject),
                _resource_kind(type_values),
                str(module) if module is not None else None,
                str(status) if status is not None else None,
                labels.get("en"),
                labels.get("zh"),
                definitions.get("en"),
                definitions.get("zh"),
            )
        )

    database_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_file) as connection:
        _create_schema(connection)
        connection.execute("DELETE FROM ontology_documents")
        connection.execute("DELETE FROM namespaces")
        connection.execute("DELETE FROM statements")
        connection.execute("DELETE FROM resources")
        connection.executemany(
            "INSERT INTO namespaces(prefix, namespace_iri) VALUES (?, ?)",
            sorted(_prefixes(context).items()),
        )
        connection.executemany(
            """
            INSERT INTO resources(
                iri, local_name, resource_type, module, status,
                label_en, label_zh, definition_en, definition_zh
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            resource_rows,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO statements(
                subject_iri, predicate_iri, object_value,
                object_kind, language, datatype_iri
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            statement_rows,
        )
        connection.execute(
            """
            INSERT INTO ontology_documents(
                ontology_iri, version, source_sha256, loaded_at, source_path, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _expand(payload["@id"], context),
                str(payload.get("versionInfo", "")),
                sha256(raw).hexdigest(),
                datetime.now(timezone.utc).isoformat(),
                str(source_file.resolve()),
                raw.decode("utf-8"),
            ),
        )

    return OntologyStore(database_file).summary()
