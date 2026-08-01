"""FastAPI application factory for the mazu-saudi v1 backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_dashboard,
    routes_hazards,
    routes_knowledge_graph,
    routes_models,
    routes_monitor,
    routes_predictions,
    routes_regions,
)
from app.settings import settings
from app.repositories.monitor_snapshot_store import monitor_snapshot_store
from app.services.monitor_acquisition import MonitorAcquisitionService
from app.services.monitor_scheduler import MonitorScheduler


def create_app(*, monitor_scheduler_enabled: bool | None = None) -> FastAPI:
    scheduler_enabled = (
        settings.monitor_scheduler_enabled
        if monitor_scheduler_enabled is None
        else monitor_scheduler_enabled
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        scheduler = None
        if scheduler_enabled:
            scheduler = MonitorScheduler(MonitorAcquisitionService(monitor_snapshot_store))
            scheduler.start()
        yield
        if scheduler is not None:
            await scheduler.stop()

    app = FastAPI(title="mazu-saudi backend", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_regions.router, prefix=settings.api_prefix)
    app.include_router(routes_hazards.router, prefix=settings.api_prefix)
    app.include_router(routes_models.router, prefix=settings.api_prefix)
    app.include_router(routes_predictions.router, prefix=settings.api_prefix)
    app.include_router(routes_knowledge_graph.router, prefix=settings.api_prefix)
    app.include_router(routes_monitor.router, prefix=settings.api_prefix)
    app.include_router(routes_dashboard.router, prefix=settings.api_prefix)

    return app


app = create_app()
