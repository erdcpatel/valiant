"""
Base Workflow and Step decorator definitions.
"""
from typing import Dict, List, Optional, Callable, Any, Union
import functools
import inspect
from .models import (
    InputField,
    StepConfig,
    StepResult,
    StepStatus,
    StepPriority,
)
from .context import WorkflowContext


def step(
    name: Optional[str] = None,
    order: int = 100,
    timeout: float = 60.0,
    retries: int = 0,
    parallel_group: Optional[str] = None,
    requires: Optional[List[str]] = None,
    priority: StepPriority = StepPriority.MEDIUM,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    condition: Optional[str] = None,
    enabled: bool = True,
    requires_approval: bool = False,
    approval_prompt: Optional[str] = None,
    approval_roles: Optional[List[str]] = None
):
    """
    Decorator to mark a method as an executable workflow step.
    """
    def decorator(func: Callable):
        step_name = name or func.__name__.replace("_", " ").title()
        config = StepConfig(
            name=step_name,
            order=order,
            timeout=timeout,
            retries=retries,
            parallel_group=parallel_group,
            requires=requires or [],
            priority=priority,
            description=description or (func.__doc__.strip() if func.__doc__ else None),
            tags=tags or [],
            condition=condition,
            enabled=enabled,
            requires_approval=requires_approval,
            approval_prompt=approval_prompt,
            approval_roles=approval_roles or []
        )

        func._is_step = True
        func._step_config = config

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._is_step = True
        wrapper._step_config = config
        return wrapper

    return decorator


_GLOBAL_REGISTRY: Dict[str, type] = {}


def workflow(name: Optional[str] = None, description: Optional[str] = None, tags: Optional[List[str]] = None):
    """
    Decorator to register a Workflow class.
    """
    def decorator(cls: type):
        wf_name = name or cls.__name__
        if description:
            cls.description = description
        if tags:
            cls.tags = tags
        cls.workflow_id = wf_name
        _GLOBAL_REGISTRY[wf_name] = cls
        return cls

    return decorator


def get_global_registry() -> Dict[str, type]:
    return _GLOBAL_REGISTRY


class Workflow:
    """
    Base class for all Valiant workflows.
    Subclasses define their steps using the @step decorator.
    """
    workflow_id: str = "workflow"
    name: str = "Base Workflow"
    description: str = "No description provided"
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = []
    profiles: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        self._current_step_logs: List[str] = []

    def get_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Return preset parameter profiles (e.g., dev, uat, prod) for this workflow."""
        return getattr(self, "profiles", {}) or {}

    def inputs(self) -> List[InputField]:
        """Override to define workflow input parameters."""
        return []

    def setup(self, context: WorkflowContext) -> None:
        """Hook called immediately before any step runs."""
        pass

    def teardown(self, context: WorkflowContext) -> None:
        """Hook called after all steps finish."""
        pass

    # --- Step Result Helper Methods ---
    def success(
        self,
        message: str = "Step succeeded",
        data: Any = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> StepResult:
        res = StepResult(
            name="",
            status=StepStatus.SUCCESS,
            success=True,
            message=message,
            data=data,
            metrics=metrics or {},
            tags=tags or []
        )
        return res

    def failure(
        self,
        message: str = "Step failed",
        error: Optional[str] = None,
        data: Any = None,
        metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> StepResult:
        res = StepResult(
            name="",
            status=StepStatus.FAILED,
            success=False,
            message=message,
            error=error or message,
            data=data,
            metrics=metrics or {},
            tags=tags or []
        )
        return res

    def skip(self, message: str = "Step skipped") -> StepResult:
        res = StepResult(
            name="",
            status=StepStatus.SKIPPED,
            success=True,
            message=message,
            skipped=True
        )
        return res

    def get_steps(self) -> List[tuple[StepConfig, Callable]]:
        """Discover and return all @step methods sorted by order."""
        steps = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if getattr(attr, "_is_step", False) and hasattr(attr, "_step_config"):
                steps.append((attr._step_config, attr))
        steps.sort(key=lambda s: (s[0].order, s[0].name))
        return steps
