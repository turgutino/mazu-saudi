"""Read-only application service for browsing the versioned weather ontology."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Any

from mazu_saudi.ontology import OntologyStore, materialize_ontology


RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def _local_name(iri: str) -> str:
    for separator in ("#", "/", ":"):
        if separator in iri:
            iri = iri.rsplit(separator, 1)[-1]
    return iri


class OntologyBrowserService:
    """Materialize the canonical source when needed and expose bounded graph views."""

    def __init__(self, source_file: Path, database_file: Path):
        self.source_file = Path(source_file)
        self.database_file = Path(database_file)
        self.store = OntologyStore(self.database_file)
        self._materialize_lock = Lock()

    def ensure_ready(self) -> dict[str, Any]:
        if not self.source_file.is_file():
            raise RuntimeError(f"Ontology source not found: {self.source_file}")
        source_digest = sha256(self.source_file.read_bytes()).hexdigest()
        with self._materialize_lock:
            try:
                summary = self.store.summary()
                current_digest = (summary.get("ontology") or {}).get("source_sha256")
            except (sqlite3.Error, OSError):
                current_digest = None
            if current_digest != source_digest:
                summary = materialize_ontology(self.source_file, self.database_file)
        return summary

    def summary(self) -> dict[str, Any]:
        summary = self.ensure_ready()
        summary["boundary"] = (
            "Observational mechanism applicability and provenance; "
            "not automatically discovered causality or forecast truth."
        )
        return summary

    def graph(
        self,
        *,
        query: str | None = None,
        module: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        summary = self.ensure_ready()
        seeds = self.store.list_resources(module=module, query=query, limit=limit)
        seed_iris = {resource["iri"] for resource in seeds}
        relationships = self.store.relationships_for(seed_iris, limit=max(1000, limit * 20))

        # A search result is shown with its immediate ontology neighborhood. An
        # unfiltered request already contains the full bounded resource set.
        if query:
            related_iris = {
                iri
                for statement in relationships
                for iri in (statement["subject_iri"], statement["object_value"])
            }
            resources = self.store.resources_by_iris(related_iris | seed_iris)
        else:
            resources = seeds

        resource_iris = {resource["iri"] for resource in resources}
        edges = [
            {
                "id": statement["id"],
                "source": statement["subject_iri"],
                "target": statement["object_value"],
                "predicate": statement["predicate_iri"],
                "predicate_label": _local_name(statement["predicate_iri"]),
            }
            for statement in relationships
            if statement["predicate_iri"] != RDF_TYPE
            and statement["subject_iri"] in resource_iris
            and statement["object_value"] in resource_iris
        ]
        nodes = [
            {
                **resource,
                "label": resource["label_zh"] or resource["label_en"] or resource["local_name"],
            }
            for resource in resources
        ]
        return {
            "ontology": summary["ontology"],
            "filters": {"query": query or "", "module": module},
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def resource(self, iri: str) -> dict[str, Any] | None:
        self.ensure_ready()
        resource = self.store.get_resource(iri)
        if resource is None:
            return None
        return {
            "resource": resource,
            "statements": self.store.statements_for(iri),
        }
