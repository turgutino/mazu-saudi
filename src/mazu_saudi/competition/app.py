"""FastAPI entrypoint for the MAZU Saudi historical warning console."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mazu_saudi.knowledge_graph import KnowledgeGraphStore

from .adapters import CITIES, HAZARDS
from .knowledge_graph_service import KnowledgeGraphBrowserService
from .ontology_service import OntologyBrowserService
from .reports import REPORT_LIBRARY, render_evidence_json, render_run_report
from .service import HistoricalWarningService, SCENARIOS
from .settings import AppSettings
from .storage import AuditStore


Locale = Literal["zh", "en"]
Hazard = Literal["heatwave", "flash_flood", "dust_storm"]
FieldLayer = Literal["probability", "rule_risk", "uncertainty"]


class RunRequest(BaseModel):
    city: str
    target_date: str = Field(pattern=r"^2025-\d{2}-\d{2}$")
    hazard: Hazard
    locale: Locale = "zh"


class AssistantRequest(BaseModel):
    run_id: str
    message: str = Field(min_length=1, max_length=2000)
    locale: Locale = "zh"


def create_app(
    settings: AppSettings | None = None,
    store: AuditStore | None = None,
    adapter=None,
) -> FastAPI:
    settings = settings or AppSettings()
    store = store or AuditStore(settings.database_file, settings.artifact_root)
    service = HistoricalWarningService(settings, store, adapter)
    ontology_service = OntologyBrowserService(
        settings.ontology_source_file,
        settings.ontology_database_file,
    )
    knowledge_graph_service = KnowledgeGraphBrowserService(
        KnowledgeGraphStore(settings.ontology_database_file),
        ontology_service,
    )
    app = FastAPI(
        title="MAZU Saudi Historical Warning Console",
        version="1.0.0",
        description="2025 historical exercise API. Not an operational warning.",
    )
    app.state.settings = settings
    app.state.store = store
    app.state.service = service
    app.state.ontology_service = ontology_service
    app.state.knowledge_graph_service = knowledge_graph_service

    @app.get("/api/v1/health")
    def health():
        preflight = settings.preflight()
        return {
            "status": "ok" if preflight["ready_for_inference"] else "degraded",
            **preflight,
            "database": "ready",
            "boundary": "2025 historical exercise; not an operational warning",
        }

    @app.get("/api/v1/config")
    def config():
        return {
            "product": {
                "name": "MAZU Saudi Historical Warning Console",
                "name_zh": "MAZU 沙特历史预警演练台",
            },
            "cities": list(CITIES),
            "hazards": list(HAZARDS),
            "date_range": {"start": "2025-01-02", "end": "2025-12-31"},
            "locales": ["zh", "en"],
            "mode": settings.preflight()["mode"],
            "boundaries": [
                "Historical Exercise / 历史演练",
                "2025 historical data",
                "Not an operational warning",
                "Proxy labels are not independent disaster truth",
            ],
        }

    @app.get("/api/v1/scenarios")
    def scenarios():
        return SCENARIOS

    @app.get("/api/v1/ontology")
    def ontology_summary():
        try:
            return ontology_service.summary()
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/v1/ontology/view")
    def ontology_relation_view(
        query: Annotated[str | None, Query(max_length=120)] = None,
        module: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 200,
    ):
        try:
            return ontology_service.relation_view(query=query, module=module, limit=limit)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/v1/ontology/graph", include_in_schema=False)
    def legacy_ontology_graph(
        query: Annotated[str | None, Query(max_length=120)] = None,
        module: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 200,
    ):
        """Keep cached pre-rename clients working without advertising the old name."""
        try:
            return ontology_service.relation_view(query=query, module=module, limit=limit)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/v1/knowledge-graph")
    def knowledge_graph_summary():
        try:
            return knowledge_graph_service.summary()
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/v1/knowledge-graph/view")
    def knowledge_graph_view(
        build_id: Annotated[str | None, Query(max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=2000)] = 500,
    ):
        try:
            return knowledge_graph_service.view(build_id=build_id, limit=limit)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/v1/ontology/resource")
    def ontology_resource(iri: Annotated[str, Query(min_length=1, max_length=500)]):
        try:
            resource = ontology_service.resource(iri)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
        if resource is None:
            raise HTTPException(404, "Ontology resource not found")
        return resource

    @app.post("/api/v1/runs", status_code=201)
    def create_run(request: RunRequest):
        if request.city not in CITIES:
            raise HTTPException(422, f"Unknown city: {request.city}")
        if not ("2025-01-02" <= request.target_date <= "2025-12-31"):
            raise HTTPException(422, "target_date must be between 2025-01-02 and 2025-12-31")
        try:
            return service.create_run(
                request.city, request.target_date, request.hazard, request.locale
            )
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/v1/runs")
    def list_runs(limit: Annotated[int, Query(ge=1, le=100)] = 50):
        return store.list_runs(limit)

    @app.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str):
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(404, "Run not found")
        return run

    @app.get("/api/v1/runs/{run_id}/field")
    def get_field(run_id: str, layer: FieldLayer = "probability"):
        run = store.get_run(run_id)
        if run is None or run["status"] != "complete":
            raise HTTPException(404, "Completed run not found")
        try:
            return service.adapter.field(run["target_date"], run["hazard"], layer)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/v1/runs/{run_id}/evidence")
    def get_evidence(run_id: str):
        run = store.get_run(run_id)
        if run is None or run["result"] is None:
            raise HTTPException(404, "Run not found")
        return run["result"]["evidence"]

    @app.post("/api/v1/runs/{run_id}/cap")
    def create_cap(run_id: str):
        run = store.get_run(run_id)
        if run is None or run["status"] != "complete":
            raise HTTPException(404, "Completed run not found")
        result = service.adapter.cap(run["city"], run["target_date"], run["hazard"])
        if not result.get("alert_warranted"):
            return result
        if "<status>Exercise</status>" not in result["cap_xml"] or "<status>Actual</status>" in result["cap_xml"]:
            raise HTTPException(500, "CAP safety boundary violation")
        artifact = store.save_artifact(
            run_id,
            "cap",
            "application/xml",
            f"MAZU-{run['hazard']}-{run['city']}-{run['target_date']}.xml",
            result["cap_xml"],
        )
        return {**result, "artifact": artifact}

    @app.post("/api/v1/assistant/messages")
    def assistant_message(request: AssistantRequest):
        run = store.get_run(request.run_id)
        if run is None or run["status"] != "complete":
            raise HTTPException(404, "Completed run not found")
        store.save_message(request.run_id, "user", request.message, "user")
        content, mode = service.assistant_response(run, request.message, request.locale)
        message = store.save_message(request.run_id, "assistant", content, mode)
        return {
            **message,
            "llm_available": settings.preflight()["llm_available"],
            "note": "Evidence-grounded analysis over frozen results; forecast values are unchanged.",
        }

    @app.get("/api/v1/reports")
    def list_reports():
        return REPORT_LIBRARY

    @app.post("/api/v1/runs/{run_id}/report")
    def create_report(run_id: str):
        run = store.get_run(run_id)
        if run is None or run["status"] != "complete":
            raise HTTPException(404, "Completed run not found")
        html_artifact = store.save_artifact(
            run_id,
            "report",
            "text/html; charset=utf-8",
            f"MAZU-{run['city']}-{run['hazard']}-{run['target_date']}.html",
            render_run_report(run),
        )
        json_artifact = store.save_artifact(
            run_id,
            "evidence",
            "application/json",
            f"MAZU-{run['city']}-{run['hazard']}-{run['target_date']}.json",
            render_evidence_json(run),
        )
        return {"report": html_artifact, "evidence": json_artifact}

    @app.get("/api/v1/artifacts/{artifact_id}")
    def get_artifact(artifact_id: str):
        artifact = store.get_artifact(artifact_id)
        if artifact is None:
            raise HTTPException(404, "Artifact not found")
        path = Path(artifact["path"])
        if not path.is_file() or settings.artifact_root.resolve() not in path.resolve().parents:
            raise HTTPException(404, "Artifact file not found")
        return FileResponse(path, media_type=artifact["media_type"], filename=artifact["filename"])

    reports_dir = settings.research_assets_root / "reports"
    if reports_dir.is_dir():
        app.mount("/reports-static", StaticFiles(directory=reports_dir), name="reports-static")
    if settings.frontend_dist.is_dir():
        assets = settings.frontend_dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

        @app.get("/{spa_path:path}", include_in_schema=False)
        def frontend(spa_path: str):
            if spa_path.startswith("api/"):
                raise HTTPException(404, "API route not found")
            candidate = (settings.frontend_dist / spa_path).resolve()
            if (
                candidate.is_file()
                and settings.frontend_dist.resolve() in candidate.parents
            ):
                return FileResponse(candidate, headers={"Cache-Control": "no-store"})
            return FileResponse(
                settings.frontend_dist / "index.html",
                headers={"Cache-Control": "no-store"},
            )

    return app


app = create_app()
