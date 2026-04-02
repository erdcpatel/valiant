"""Type-safe execution context passed through all steps."""
from __future__ import annotations

from typing import Any

from valiant.core.models import StepResult


class WorkflowContext:
    """
    Holds workflow inputs and accumulates step results as execution proceeds.

    Replaces the raw `dict` context from v2 with a typed, accessor-safe wrapper.
    Steps access inputs via ctx["key"] and previous step data via ctx.get_data().
    """

    def __init__(self, inputs: dict[str, Any], workflow_name: str = "") -> None:
        self._inputs: dict[str, Any] = dict(inputs)
        self._results: dict[str, StepResult] = {}
        self.workflow_name = workflow_name

    # ── Input access ──────────────────────────────────────────────────────────

    def __getitem__(self, key: str) -> Any:
        return self._inputs[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._inputs.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._inputs

    @property
    def inputs(self) -> dict[str, Any]:
        """Read-only view of workflow inputs."""
        return dict(self._inputs)

    # ── Step result access ────────────────────────────────────────────────────

    def get_result(self, step_name: str) -> StepResult | None:
        """Return the StepResult for a completed step, or None."""
        return self._results.get(step_name)

    def get_data(self, step_name: str, key: str | None = None) -> Any:
        """
        Return data from a previous step.
        - get_data("Fetch Users")          → the full data dict
        - get_data("Fetch Users", "count") → a specific key within data
        """
        result = self._results.get(step_name)
        if result is None:
            return None
        if key is None:
            return result.data
        return result.data.get(key)

    def get_metric(self, step_name: str, metric: str) -> float | None:
        result = self._results.get(step_name)
        if result is None:
            return None
        return result.metrics.get(metric)

    # ── Internal mutation (used by runner only) ───────────────────────────────

    def _record_result(self, result: StepResult) -> None:
        self._results[result.name] = result

    @property
    def completed_steps(self) -> list[str]:
        return list(self._results.keys())

    def __repr__(self) -> str:
        return (
            f"WorkflowContext(workflow={self.workflow_name!r}, "
            f"inputs={list(self._inputs.keys())}, "
            f"completed={self.completed_steps})"
        )
