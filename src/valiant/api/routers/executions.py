from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from valiant.api.auth import require_api_key
from valiant.api.schemas import RunResponse, RunSummaryResponse, StepResultResponse
from valiant.core.exceptions import WorkflowNotFoundError, WorkflowValidationError
from valiant.core.registry import registry
from valiant.core.runner import WorkflowRunner
from valiant.storage import RunRepository, get_session
from valiant.storage.models import WorkflowRun

router = APIRouter(prefix="/runs", tags=["executions"])


def _sensitive_names(workflow_name: str) -> set[str]:
    try:
        meta = registry.get_meta(workflow_name)
        return {f.name for f in meta.input_fields if f.sensitive}
    except WorkflowNotFoundError:
        return set()


def _step_response(step_dict: dict[str, Any]) -> StepResultResponse:
    return StepResultResponse(
        name=step_dict.get("step_name", ""),
        status=step_dict.get("status", ""),
        message=step_dict.get("message", ""),
        duration_ms=step_dict.get("duration_ms", 0.0),
        attempts=step_dict.get("attempts", 1),
        metrics=step_dict.get("metrics", {}),
        tags=step_dict.get("tags", []),
        error=step_dict.get("error"),
    )


def _run_to_response(run: WorkflowRun, steps: list) -> RunResponse:
    return RunResponse(
        run_id=run.run_id,
        workflow_name=run.workflow_name,
        status=run.status,
        triggered_by=run.triggered_by,
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_duration_ms=run.duration_ms,
        steps=[_step_response(s.to_dict()) for s in steps],
        error=run.error,
    )


@router.post("/{workflow_name}", response_model=RunResponse, status_code=status.HTTP_200_OK)
def run_workflow(
    workflow_name: str,
    inputs: dict[str, Any] = {},
    _key: str = Depends(require_api_key),
    session: Session = Depends(get_session),
) -> RunResponse:
    try:
        workflow_cls = registry.get_class(workflow_name)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    runner = WorkflowRunner()
    try:
        result = runner.run(workflow_cls, inputs, triggered_by="api")
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {exc}") from exc

    repo = RunRepository(session)
    sensitive = _sensitive_names(workflow_name)
    run_record = repo.save_with_inputs(result, inputs, sensitive)
    steps = repo.get_steps(result.run_id)

    return _run_to_response(run_record, steps)


@router.get("", response_model=list[RunSummaryResponse])
def list_runs(
    workflow: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _key: str = Depends(require_api_key),
    session: Session = Depends(get_session),
) -> list[RunSummaryResponse]:
    repo = RunRepository(session)
    runs = repo.list_runs(workflow_name=workflow, status=status_filter, limit=limit, offset=offset)
    return [
        RunSummaryResponse(
            run_id=r.run_id,
            workflow_name=r.workflow_name,
            status=r.status,
            triggered_by=r.triggered_by,
            started_at=r.started_at,
            duration_ms=r.duration_ms,
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    _key: str = Depends(require_api_key),
    session: Session = Depends(get_session),
) -> RunResponse:
    repo = RunRepository(session)
    run = repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    steps = repo.get_steps(run_id)
    return _run_to_response(run, steps)
