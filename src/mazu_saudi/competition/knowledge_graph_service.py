"""Read-only service for browsing staged knowledge-graph evidence."""

from __future__ import annotations

from typing import Any

from mazu_saudi.knowledge_graph import KnowledgeGraphStore, KWGBackgroundStore

from .ontology_service import OntologyBrowserService


class KnowledgeGraphBrowserService:
    def __init__(
        self,
        store: KnowledgeGraphStore,
        ontology_service: OntologyBrowserService,
        background_store: KWGBackgroundStore | None = None,
    ):
        self.store = store
        self.ontology_service = ontology_service
        self.background_store = background_store or KWGBackgroundStore(
            store.database_file
        )

    def summary(self) -> dict[str, Any]:
        self.ontology_service.ensure_ready()
        build = self.store.latest_build()
        return {
            "build": build,
            "available": build is not None,
            "external_background": self.background_store.latest_run(),
            "boundary": (
                "Data-derived relations are classified as diagnostic evidence, "
                "statistical evidence, or Saudi offline-evaluation candidates. "
                "They are not causal mechanisms; no automatic relation is "
                "transferable or production-ready."
            ),
        }

    def view(self, *, build_id: str | None = None, limit: int = 500) -> dict[str, Any]:
        self.ontology_service.ensure_ready()
        return self.store.graph_view(build_id, limit=limit)

    def background_summary(self) -> dict[str, Any]:
        latest = self.background_store.latest_run()
        active = self.background_store.latest_available_run()
        return {
            "run": latest,
            "active_run": active,
            "available": active is not None,
            "boundary": (
                "KWG records are external geography or historical background. "
                "They are not MAZU observation truth, causal evidence, or "
                "production prediction rules."
            ),
        }

    def background_view(self, *, run_id: str | None = None) -> dict[str, Any]:
        return self.background_store.background_view(run_id)
