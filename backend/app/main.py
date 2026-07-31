"""FastAPI application factory for the mazu-saudi v1 backend."""

from __future__ import annotations

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


def create_app() -> FastAPI:
    app = FastAPI(title="mazu-saudi backend", version="1.0.0")

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
