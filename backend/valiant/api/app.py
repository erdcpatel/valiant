"""
FastAPI application entry point.
"""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from contextlib import asynccontextmanager

from .routers.workflows import router as workflows_router
from .routers.runs import router as runs_router
from .routers.ws import router as ws_router
from .routers.auth import router as auth_router
from .routers.environments import router as environments_router
from .routers.schedules import router as schedules_router
from .routers.webhooks import router as webhooks_router
from ..core.registry import registry
from ..core.scheduler import scheduler
from ..db.database import init_db
from .. import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initialize DB, discover workflows, launch and shutdown scheduler."""
    init_db()
    registry.discover()
    scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(
    title="ValiantFlow Workflow Platform",
    description="Developer-first Workflow Automation & Orchestration Platform",
    version=__version__,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under /api
app.include_router(auth_router, prefix="/api")
app.include_router(environments_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(runs_router, prefix="/api")
app.include_router(schedules_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(ws_router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "valiantflow-api",
        "version": __version__
    }


# Static Frontend Mounting
# Check repository root frontend/dist first (development), then bundled package data web/ (installed wheel)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
BUNDLED_WEB = Path(__file__).resolve().parent.parent / "web"

STATIC_DIR = None
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    STATIC_DIR = FRONTEND_DIST
elif BUNDLED_WEB.exists() and (BUNDLED_WEB / "index.html").exists():
    STATIC_DIR = BUNDLED_WEB

if STATIC_DIR:
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        # Don't hijack /api, /docs, /openapi.json, or /redoc
        if (
            full_path == "api"
            or full_path.startswith("api/")
            or full_path == "docs"
            or full_path.startswith("docs/")
            or full_path == "openapi.json"
            or full_path.startswith("redoc")
        ):
            return JSONResponse({"error": "Not found"}, status_code=404)

        target_file = STATIC_DIR / full_path
        if target_file.exists() and target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def index():
        return {
            "message": "ValiantFlow Workflow Platform API is running.",
            "docs_url": "/docs",
            "frontend_status": "Frontend not built yet. Run 'npm run build' inside frontend/"
        }
