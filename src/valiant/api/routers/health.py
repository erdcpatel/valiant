from __future__ import annotations

from fastapi import APIRouter

from valiant.api.schemas import HealthResponse, StatsResponse
from valiant.core.registry import registry
from valiant.storage import RunRepository, get_session

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="3.0.0",
        workflow_count=len(registry),
        database="connected",
    )


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    session_gen = get_session()
    session = next(session_gen)
    try:
        repo = RunRepository(session)
        total = repo.count_runs()
        success = repo.count_runs(status="success")
        failed = repo.count_runs(status="failed")
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass

    return StatsResponse(
        total_runs=total,
        success_runs=success,
        failed_runs=failed,
        workflows=registry.names(),
    )
