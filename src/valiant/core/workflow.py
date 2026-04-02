"""
Workflow base class and @step / @workflow decorators.

Clean rewrite — single implementation, no legacy fallbacks, no dead code.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Callable

from valiant.core.context import WorkflowContext
from valiant.core.models import InputField, StepResult


# ── Step configuration ─────────────────────────────────────────────────────────

@dataclass
class StepConfig:
    name: str
    order: int = 0
    requires: list[str] = field(default_factory=list)
    parallel_group: str | None = None
    timeout: float | None = None
    retries: int = 1
    description: str = ""


# ── @step decorator ────────────────────────────────────────────────────────────

def step(
    name: str,
    order: int = 0,
    requires: list[str] | None = None,
    parallel_group: str | None = None,
    timeout: float | None = None,
    retries: int = 1,
    description: str = "",
) -> Callable:
    """
    Marks a Workflow method as an executable step.

    Usage::

        @step(name="Validate Input", order=1)
        def validate(self, ctx: WorkflowContext) -> StepResult:
            return self.success("Validated", metrics={"count": 5})

        @step(name="Load A", order=2, parallel_group="loaders", requires=["Validate Input"])
        def load_a(self, ctx: WorkflowContext) -> StepResult: ...

        @step(name="Load B", order=2, parallel_group="loaders", requires=["Validate Input"])
        def load_b(self, ctx: WorkflowContext) -> StepResult: ...
    """

    def decorator(func: Callable) -> Callable:
        config = StepConfig(
            name=name,
            order=order,
            requires=requires or [],
            parallel_group=parallel_group,
            timeout=timeout,
            retries=retries,
            description=description,
        )

        @functools.wraps(func)
        def wrapper(self: "Workflow", ctx: WorkflowContext) -> StepResult:
            self._current_step_name = name
            result = func(self, ctx)
            # Ensure name is set — even if developer returns a bare StepResult
            if isinstance(result, StepResult):
                return result.model_copy(update={"name": name})
            # If step returned None (mistake), treat as success with no message
            return StepResult(name=name, success=True, message="(no return value)")

        wrapper._step_config = config  # type: ignore[attr-defined]
        return wrapper

    return decorator


# ── Workflow base class ────────────────────────────────────────────────────────

class Workflow:
    """
    Base class for all Valiant workflows.

    Subclass this, decorate steps with @step, and optionally override
    get_input_fields() to declare the inputs your workflow expects.

    Example::

        @workflow(name="my_workflow", description="Does something useful")
        class MyWorkflow(Workflow):
            def get_input_fields(self) -> list[InputField]:
                return [InputField(name="username", required=True)]

            @step(name="Greet", order=1)
            def greet(self, ctx: WorkflowContext) -> StepResult:
                return self.success(f"Hello {ctx['username']}!", metrics={"length": 5})
    """

    _current_step_name: str = ""

    def get_input_fields(self) -> list[InputField]:
        """Override to declare workflow inputs. Return empty list for no inputs."""
        return []

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, str]:
        """
        Validate raw inputs against field definitions.
        Returns a dict of {field_name: error_message} — empty dict means valid.
        """
        errors: dict[str, str] = {}
        for field_def in self.get_input_fields():
            value = inputs.get(field_def.name)
            valid, message = field_def.validate_value(value)
            if not valid:
                errors[field_def.name] = message
        return errors

    # ── Step result helpers ────────────────────────────────────────────────────

    def success(
        self,
        message: str,
        data: dict[str, Any] | None = None,
        metrics: dict[str, float] | None = None,
        tags: list[str] | None = None,
    ) -> StepResult:
        return StepResult(
            name=self._current_step_name,
            success=True,
            message=message,
            data=data or {},
            metrics=metrics or {},
            tags=tags or [],
        )

    def failure(
        self,
        message: str,
        data: dict[str, Any] | None = None,
        metrics: dict[str, float] | None = None,
        tags: list[str] | None = None,
        error: str | None = None,
    ) -> StepResult:
        return StepResult(
            name=self._current_step_name,
            success=False,
            message=message,
            data=data or {},
            metrics=metrics or {},
            tags=tags or [],
            error=error,
        )

    def skip(self, reason: str) -> StepResult:
        return StepResult(
            name=self._current_step_name,
            success=True,
            skipped=True,
            message=reason,
        )

    # ── Step discovery ─────────────────────────────────────────────────────────

    @classmethod
    def discover_steps(cls) -> list[tuple[Callable, StepConfig]]:
        """Return all @step-decorated methods sorted by order."""
        steps = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)
            if callable(attr) and hasattr(attr, "_step_config"):
                steps.append((attr, attr._step_config))
        return sorted(steps, key=lambda x: (x[1].order, x[1].name))


# ── @workflow decorator + registry helper ─────────────────────────────────────

_WORKFLOW_REGISTRY: dict[str, type[Workflow]] = {}


def workflow(
    name: str,
    description: str = "",
    tags: list[str] | None = None,
    version: str = "1.0.0",
) -> Callable[[type[Workflow]], type[Workflow]]:
    """
    Registers a Workflow class under a canonical name.

    Usage::

        @workflow(name="data_pipeline", description="Runs the ETL pipeline")
        class DataPipelineWorkflow(Workflow): ...
    """

    def decorator(cls: type[Workflow]) -> type[Workflow]:
        cls._workflow_name = name  # type: ignore[attr-defined]
        cls._workflow_description = description  # type: ignore[attr-defined]
        cls._workflow_tags = tags or []  # type: ignore[attr-defined]
        cls._workflow_version = version  # type: ignore[attr-defined]

        if name in _WORKFLOW_REGISTRY:
            from valiant.core.exceptions import WorkflowAlreadyRegisteredError
            raise WorkflowAlreadyRegisteredError(name)

        _WORKFLOW_REGISTRY[name] = cls
        return cls

    return decorator


def get_registered_workflows() -> dict[str, type[Workflow]]:
    """Return a copy of the current registry."""
    return dict(_WORKFLOW_REGISTRY)


def clear_registry() -> None:
    """For testing only."""
    _WORKFLOW_REGISTRY.clear()
