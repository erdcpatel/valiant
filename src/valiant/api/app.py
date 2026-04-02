"""FastAPI application factory."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from valiant.api.routers import executions, health, workflows
from valiant.config import settings
from valiant.core.registry import registry
from valiant.storage import init_db

log = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    from valiant.logging_setup import configure_logging
    configure_logging()

    # Initialise DB and load workflows eagerly so the app is ready
    # regardless of whether ASGI lifespan events fire (e.g. in tests).
    init_db()
    registry.load_builtins()
    for directory in settings.extra_workflow_dirs:
        registry.load_directory(directory)

    app = FastAPI(
        title="Valiant Workflow Platform",
        description="Production-ready workflow automation API",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — explicit origins, never wildcard + credentials together
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(workflows.router)
    app.include_router(executions.router)

    @app.on_event("startup")
    async def startup() -> None:
        log.info(
            "api.started",
            workflows=registry.names(),
            auth_enabled=settings.auth_enabled,
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "name": "Valiant Workflow Platform",
            "version": "3.0.0",
            "docs": "/docs",
            "health": "/health",
            "workflows": "/workflows",
        }

    return app


# Module-level app instance (for uvicorn)
app = create_app()
