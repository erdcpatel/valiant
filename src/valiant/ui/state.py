"""Shared Taipy GUI state — one typed object drives the entire UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    # ── Workflow catalog ──────────────────────────────────
    workflow_names: list[str] = field(default_factory=list)
    selected_workflow: str = ""
    workflow_description: str = ""
    workflow_tags: str = ""
    workflow_version: str = ""

    # ── Dynamic input form ────────────────────────────────
    input_fields: list[dict[str, Any]] = field(default_factory=list)
    # Flat dict of current form values (field_name -> value)
    form_values: dict[str, Any] = field(default_factory=dict)
    form_error: str = ""

    # ── Execution state ───────────────────────────────────
    is_running: bool = False
    run_status: str = ""          # "", "running", "success", "partial", "failed"
    run_id: str = ""
    current_step: str = ""
    step_results: list[dict[str, Any]] = field(default_factory=list)
    run_duration: str = ""
    run_error: str = ""

    # ── Dashboard stats ───────────────────────────────────
    total_runs: int = 0
    success_runs: int = 0
    failed_runs: int = 0
    success_rate: str = "0%"

    # ── History ───────────────────────────────────────────
    history_rows: list[dict[str, Any]] = field(default_factory=list)
    history_filter_workflow: str = "All"
    history_filter_status: str = "All"
    history_limit: int = 50

    # ── Notifications ─────────────────────────────────────
    notification: str = ""
    notification_type: str = "info"   # info | success | error | warning
