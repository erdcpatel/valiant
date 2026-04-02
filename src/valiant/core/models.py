"""Core Pydantic models — single source of truth, no duplicates."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class InputType(str, Enum):
    TEXT = "text"
    PASSWORD = "password"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    DATE = "date"
    EMAIL = "email"
    TEXTAREA = "textarea"


class InputField(BaseModel):
    """Describes one input parameter a workflow expects."""

    name: str
    label: str = ""
    type: InputType = InputType.TEXT
    required: bool = True
    default: Any = None
    description: str = ""
    options: list[str] = Field(default_factory=list)  # for SELECT type
    min_value: float | None = None  # for NUMBER type
    max_value: float | None = None  # for NUMBER type
    sensitive: bool = False  # marks field as secret — redacted in logs/API responses

    def display_label(self) -> str:
        return self.label or self.name.replace("_", " ").title()

    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Returns (is_valid, error_message)."""
        if self.required and (value is None or value == ""):
            return False, f"'{self.display_label()}' is required"
        if self.type == InputType.NUMBER and value is not None and value != "":
            try:
                num = float(value)
            except (TypeError, ValueError):
                return False, f"'{self.display_label()}' must be a number"
            if self.min_value is not None and num < self.min_value:
                return False, f"'{self.display_label()}' must be ≥ {self.min_value}"
            if self.max_value is not None and num > self.max_value:
                return False, f"'{self.display_label()}' must be ≤ {self.max_value}"
        if self.type == InputType.SELECT and self.options and value not in self.options:
            return False, f"'{self.display_label()}' must be one of: {', '.join(self.options)}"
        return True, ""


class StepResult(BaseModel):
    """Result of a single workflow step execution."""

    name: str = ""
    success: bool = True
    skipped: bool = False
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    attempts: int = 1
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def status_label(self) -> str:
        if self.skipped:
            return "skipped"
        return "success" if self.success else "failed"

    def to_display_dict(self) -> dict[str, Any]:
        """Safe dict for display — excludes raw data payloads."""
        return {
            "step": self.name,
            "status": self.status_label,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 1),
            "attempts": self.attempts,
            "metrics": self.metrics,
            "tags": self.tags,
        }


class WorkflowResult(BaseModel):
    """Aggregated result of a complete workflow run."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_name: str
    success: bool = True
    steps: list[StepResult] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error: str | None = None
    triggered_by: str = "unknown"  # "api" | "cli" | "ui"

    @property
    def failed_steps(self) -> list[StepResult]:
        return [s for s in self.steps if not s.success and not s.skipped]

    @property
    def success_rate(self) -> float:
        non_skipped = [s for s in self.steps if not s.skipped]
        if not non_skipped:
            return 100.0
        return sum(1 for s in non_skipped if s.success) / len(non_skipped) * 100

    @property
    def status_label(self) -> str:
        if not self.steps:
            return "empty"
        if all(s.success or s.skipped for s in self.steps):
            return "success"
        if any(s.success for s in self.steps):
            return "partial"
        return "failed"


class WorkflowMeta(BaseModel):
    """Static metadata about a registered workflow."""

    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    input_fields: list[InputField] = Field(default_factory=list)
