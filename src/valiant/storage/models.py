"""SQLModel ORM models for persisting workflow execution history."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlmodel import Field, SQLModel

from valiant.core.models import StepResult, WorkflowResult


class WorkflowRun(SQLModel, table=True):
    __tablename__ = "workflow_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, unique=True)
    workflow_name: str = Field(index=True)
    status: str  # success | partial | failed | running
    triggered_by: str = "unknown"  # api | cli | ui
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    inputs_json: str = "{}"   # sanitized — sensitive values replaced with [REDACTED]
    error: Optional[str] = None

    @classmethod
    def from_result(
        cls,
        result: WorkflowResult,
        sanitized_inputs: dict[str, Any],
    ) -> "WorkflowRun":
        return cls(
            run_id=result.run_id,
            workflow_name=result.workflow_name,
            status=result.status_label,
            triggered_by=result.triggered_by,
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration_ms=round(result.total_duration_ms, 2),
            inputs_json=json.dumps(sanitized_inputs, default=str),
            error=result.error,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }


class StepRun(SQLModel, table=True):
    __tablename__ = "step_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)  # FK to workflow_runs.run_id
    step_name: str
    status: str   # success | failed | skipped
    message: str = ""
    duration_ms: float = 0.0
    attempts: int = 1
    metrics_json: str = "{}"
    tags_json: str = "[]"
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_result(cls, run_id: str, result: StepResult) -> "StepRun":
        return cls(
            run_id=run_id,
            step_name=result.name,
            status=result.status_label,
            message=result.message,
            duration_ms=round(result.duration_ms, 2),
            attempts=result.attempts,
            metrics_json=json.dumps(result.metrics),
            tags_json=json.dumps(result.tags),
            error=result.error,
            started_at=result.started_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_name": self.step_name,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "metrics": json.loads(self.metrics_json),
            "tags": json.loads(self.tags_json),
            "error": self.error,
        }
