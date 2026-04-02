"""Pydantic request/response schemas for the REST API.

These are intentionally separate from core models so we can:
- Shape API responses independently of internal data structures
- Guarantee no sensitive data leaks into responses
- Version the API independently of the core engine
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class RunWorkflowRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict, description="Workflow input values")


# ── Responses ─────────────────────────────────────────────────────────────────

class InputFieldResponse(BaseModel):
    name: str
    label: str
    type: str
    required: bool
    default: Any
    description: str
    options: list[str]
    sensitive: bool


class WorkflowSummaryResponse(BaseModel):
    name: str
    description: str
    tags: list[str]
    version: str
    step_count: int


class WorkflowDetailResponse(WorkflowSummaryResponse):
    input_fields: list[InputFieldResponse]


class StepResultResponse(BaseModel):
    name: str
    status: str
    message: str
    duration_ms: float
    attempts: int
    metrics: dict[str, float]
    tags: list[str]
    error: str | None


class RunResponse(BaseModel):
    run_id: str
    workflow_name: str
    status: str
    triggered_by: str
    started_at: datetime
    completed_at: datetime | None
    total_duration_ms: float
    steps: list[StepResultResponse]
    error: str | None


class RunSummaryResponse(BaseModel):
    run_id: str
    workflow_name: str
    status: str
    triggered_by: str
    started_at: datetime
    duration_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str
    workflow_count: int
    database: str


class StatsResponse(BaseModel):
    total_runs: int
    success_runs: int
    failed_runs: int
    workflows: list[str]
