"""Read-only service for browsing built statistical knowledge-graph instances."""

from __future__ import annotations

from typing import Any

from mazu_saudi.knowledge_graph import KnowledgeGraphStore

from .ontology_service import OntologyBrowserService


class KnowledgeGraphBrowserService:
    def __init__(
        self,
        store: KnowledgeGraphStore,
        ontology_service: OntologyBrowserService,
    ):
        self.store = store
        self.ontology_service = ontology_service

    def summary(self) -> dict[str, Any]:
        self.ontology_service.ensure_ready()
        build = self.store.latest_build()
        return {
            "build": build,
            "available": build is not None,
            "boundary": (
                "Data-derived lagged associations are observational statistics, "
                "not causal mechanisms or independently observed hazard events."
            ),
        }

    def view(self, *, build_id: str | None = None, limit: int = 500) -> dict[str, Any]:
        self.ontology_service.ensure_ready()
        return self.store.graph_view(build_id, limit=limit)
