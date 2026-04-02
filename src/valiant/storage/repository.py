"""Repository pattern — all DB access goes through here, no raw SQL elsewhere."""
from __future__ import annotations

from typing import Any

import structlog
from sqlmodel import Session, select

from valiant.core.models import WorkflowResult
from valiant.storage.models import StepRun, WorkflowRun

log = structlog.get_logger(__name__)

# Fields that must never be stored — checked by name (case-insensitive)
_SENSITIVE_KEYWORDS = {"password", "secret", "token", "key", "api_key", "auth", "credential"}


def _sanitize_inputs(inputs: dict[str, Any], sensitive_names: set[str]) -> dict[str, Any]:
    """Replace sensitive field values with [REDACTED]."""
    result = {}
    for k, v in inputs.items():
        is_sensitive = k.lower() in _SENSITIVE_KEYWORDS or k in sensitive_names
        result[k] = "[REDACTED]" if is_sensitive else v
    return result


class RunRepository:
    """Persists and queries workflow run records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        result: WorkflowResult,
        sensitive_input_names: set[str] | None = None,
    ) -> WorkflowRun:
        sanitized = _sanitize_inputs(
            result.triggered_by != "unknown" and {} or {},
            sensitive_input_names or set(),
        )
        run = WorkflowRun.from_result(result, sanitized)
        self._session.add(run)

        for step in result.steps:
            step_run = StepRun.from_result(result.run_id, step)
            self._session.add(step_run)

        self._session.commit()
        self._session.refresh(run)
        log.info("repository.saved", run_id=result.run_id, workflow=result.workflow_name)
        return run

    def save_with_inputs(
        self,
        result: WorkflowResult,
        inputs: dict[str, Any],
        sensitive_input_names: set[str] | None = None,
    ) -> WorkflowRun:
        sanitized = _sanitize_inputs(inputs, sensitive_input_names or set())
        run = WorkflowRun.from_result(result, sanitized)
        self._session.add(run)

        for step in result.steps:
            step_run = StepRun.from_result(result.run_id, step)
            self._session.add(step_run)

        self._session.commit()
        self._session.refresh(run)
        return run

    def get(self, run_id: str) -> WorkflowRun | None:
        stmt = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
        return self._session.exec(stmt).first()

    def get_steps(self, run_id: str) -> list[StepRun]:
        stmt = select(StepRun).where(StepRun.run_id == run_id)
        return list(self._session.exec(stmt).all())

    def list_runs(
        self,
        workflow_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowRun]:
        stmt = select(WorkflowRun)
        if workflow_name:
            stmt = stmt.where(WorkflowRun.workflow_name == workflow_name)
        if status:
            stmt = stmt.where(WorkflowRun.status == status)
        stmt = stmt.order_by(WorkflowRun.started_at.desc()).limit(limit).offset(offset)  # type: ignore[arg-type]
        return list(self._session.exec(stmt).all())

    def count_runs(
        self,
        workflow_name: str | None = None,
        status: str | None = None,
    ) -> int:
        from sqlmodel import func
        stmt = select(func.count()).select_from(WorkflowRun)  # type: ignore[call-overload]
        if workflow_name:
            stmt = stmt.where(WorkflowRun.workflow_name == workflow_name)
        if status:
            stmt = stmt.where(WorkflowRun.status == status)
        return self._session.exec(stmt).one()
