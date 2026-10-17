"""
Base Workflow and Step decorator definitions.
"""
from typing import Dict, List, Optional, Callable, Any, Union, get_origin, get_args, Literal
import functools
import inspect
from enum import Enum
from .models import (
    InputField,
    InputType,
    StepConfig,
    StepResult,
    StepStatus,
    StepPriority,
)
from .context import WorkflowContext


_STEP_DECLARATION_COUNTER = 0


def step(
    name: Optional[str] = None,
    order: Optional[int] = None,
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
    Decorator to mark a method or function as an executable workflow step.
    If order is omitted, steps are auto-sequenced in declaration order (10, 20, 30...).
    """
    global _STEP_DECLARATION_COUNTER

    # Support @step without parentheses: @step def my_step(...)
    actual_func = None
    if callable(name) and not isinstance(name, str):
        actual_func = name
        name = None

    assigned_order = order
    if assigned_order is None:
        _STEP_DECLARATION_COUNTER += 10
        assigned_order = _STEP_DECLARATION_COUNTER

    def decorator(func: Callable):
        step_name = name or func.__name__.replace("_", " ").title()
        config = StepConfig(
            name=step_name,
            order=assigned_order,
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

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

        wrapper._is_step = True
        wrapper._step_config = config
        return wrapper

    if actual_func is not None:
        return decorator(actual_func)
    return decorator


_GLOBAL_REGISTRY: Dict[str, Any] = {}


def get_global_registry() -> Dict[str, Any]:
    return _GLOBAL_REGISTRY


RESERVED_WORKFLOW_ATTRS = {
    "workflow_id",
    "name",
    "description",
    "version",
    "author",
    "tags",
    "profiles",
    "_current_step_logs",
    "_steps",
    "_custom_inputs",
}


def _map_annotation_to_input_field(
    attr_name: str,
    type_hint: Any,
    default_val: Any = inspect.Parameter.empty,
    docstring: Optional[str] = None
) -> InputField:
    """Map a Python type annotation and default value to a Valiant InputField."""
    # Check if default_val is already an InputField
    if isinstance(default_val, InputField):
        if not default_val.name:
            default_val.name = attr_name
        if not default_val.label:
            default_val.label = attr_name.replace("_", " ").title()
        return default_val

    # Unpack Pydantic FieldInfo if used
    help_text = docstring
    min_val = None
    max_val = None
    sensitive = False

    if hasattr(default_val, "default") and hasattr(default_val, "description"):
        help_text = default_val.description or help_text
        min_val = getattr(default_val, "ge", getattr(default_val, "gt", None))
        max_val = getattr(default_val, "le", getattr(default_val, "lt", None))
        val_default = getattr(default_val, "default", inspect.Parameter.empty)
        # Handle PydanticUndefined
        if type(val_default).__name__ == "PydanticUndefinedType":
            val_default = inspect.Parameter.empty
        default_val = val_default

    # Handle Optional[T] / Union[T, None]
    is_optional = False
    origin = get_origin(type_hint)
    if origin is Union:
        args = get_args(type_hint)
        non_none = [a for a in args if a is not type(None)]
        if type(None) in args:
            is_optional = True
        if len(non_none) == 1:
            type_hint = non_none[0]
            origin = get_origin(type_hint)

    # Determine input type & options
    input_type = InputType.TEXT
    options = None

    if origin is Literal:
        input_type = InputType.SELECT
        options = [str(arg) for arg in get_args(type_hint)]
    elif isinstance(type_hint, type) and issubclass(type_hint, Enum):
        input_type = InputType.SELECT
        options = [str(e.value) for e in type_hint]
    elif type_hint in (bool, "bool"):
        input_type = InputType.CHECKBOX
    elif type_hint in (int, float, "int", "float"):
        input_type = InputType.NUMBER
    elif type_hint in (list, dict) or origin in (list, dict):
        input_type = InputType.JSON
    elif type_hint in (str, "str"):
        input_type = InputType.TEXT

    # Detect sensitive fields from name keywords
    lower_name = attr_name.lower()
    if any(k in lower_name for k in ("password", "token", "secret", "api_key", "credential")):
        input_type = InputType.PASSWORD
        sensitive = True

    has_default = default_val is not inspect.Parameter.empty
    required = not is_optional and not has_default
    actual_default = default_val if has_default else (False if input_type == InputType.CHECKBOX else None)

    return InputField(
        name=attr_name,
        type=input_type,
        label=attr_name.replace("_", " ").title(),
        required=required,
        default=actual_default,
        help_text=help_text,
        options=options,
        min_value=min_val,
        max_value=max_val,
        sensitive=sensitive
    )


class Workflow:
    """
    Base class for all Valiant workflows.
    Subclasses can declare typed class attributes (Pydantic/Dataclass style)
    and define their steps using the @step decorator.
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
        """
        Return workflow input parameters.
        Automatically introspects type-annotated class attributes or step parameter signatures
        if not explicitly defined.
        """
        # 1. Infer from type-annotated class attributes
        inferred = self._infer_inputs_from_annotations()
        if inferred:
            return inferred

        # 2. Infer from step parameter signatures
        return self._infer_inputs_from_steps()

    def _infer_inputs_from_annotations(self) -> List[InputField]:
        """Extract typed class attributes into InputField instances."""
        fields: List[InputField] = []
        cls = self.__class__
        annotations = getattr(cls, "__annotations__", {})

        for attr_name, type_hint in annotations.items():
            if attr_name.startswith("_") or attr_name in RESERVED_WORKFLOW_ATTRS:
                continue

            default_val = getattr(cls, attr_name, inspect.Parameter.empty)
            field = _map_annotation_to_input_field(attr_name, type_hint, default_val)
            fields.append(field)

        return fields

    def _infer_inputs_from_steps(self) -> List[InputField]:
        """Infer input fields from parameters declared on step functions."""
        fields: Dict[str, InputField] = {}
        for _, func in self.get_steps():
            try:
                sig = inspect.signature(func)
                for p_name, param in sig.parameters.items():
                    if p_name in ("self", "cls", "context", "ctx") or p_name.startswith("_"):
                        continue
                    if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                        continue
                    if p_name not in fields:
                        hint = param.annotation if param.annotation is not inspect.Parameter.empty else (type(param.default) if param.default is not inspect.Parameter.empty else str)
                        field = _map_annotation_to_input_field(p_name, hint, param.default)
                        fields[p_name] = field
            except Exception:
                pass
        return list(fields.values())

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


class FunctionalWorkflow(Workflow):
    """
    A lightweight, functional micro-workflow instance allowing fluent registration
    of steps, approval gates, inputs, and environment profiles without subclassing.
    """
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        version: str = "1.0.0",
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        profiles: Optional[Dict[str, Dict[str, Any]]] = None,
        inputs: Optional[List[InputField]] = None,
    ):
        super().__init__()
        self.workflow_id = name
        self.name = name.replace("_", " ").title()
        self.description = description or f"Functional pipeline for {name}"
        self.version = version
        self.tags = tags or ["functional"]
        self.author = author
        self.profiles = profiles or {}
        self._steps: List[tuple[StepConfig, Callable]] = []
        self._custom_inputs: List[InputField] = list(inputs or [])
        _GLOBAL_REGISTRY[name] = self

    def step(
        self,
        name_or_func: Optional[Union[str, Callable]] = None,
        *,
        order: Optional[int] = None,
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
        """Register a step on this functional workflow instance."""
        global _STEP_DECLARATION_COUNTER

        actual_func = None
        s_name = None
        if callable(name_or_func) and not isinstance(name_or_func, str):
            actual_func = name_or_func
        elif isinstance(name_or_func, str):
            s_name = name_or_func

        assigned_order = order
        if assigned_order is None:
            _STEP_DECLARATION_COUNTER += 10
            assigned_order = _STEP_DECLARATION_COUNTER

        def decorator(func: Callable):
            final_name = s_name or func.__name__.replace("_", " ").title()
            cfg = StepConfig(
                name=final_name,
                order=assigned_order,
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
            func._step_config = cfg
            self._steps.append((cfg, func))
            return func

        if actual_func is not None:
            return decorator(actual_func)
        return decorator

    def approval(
        self,
        name_or_prompt: Optional[str] = None,
        *,
        prompt: Optional[str] = None,
        roles: Optional[List[str]] = None,
        order: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """Register a human-in-the-loop approval gate."""
        step_name = name_or_prompt if (prompt or name_or_prompt) else "Approval Gate"
        act_prompt = prompt or name_or_prompt or "Approve execution to proceed"

        def decorator(func: Optional[Callable] = None):
            fn = func if func is not None else (lambda ctx=None: None)
            return self.step(
                step_name,
                order=order,
                requires_approval=True,
                approval_prompt=act_prompt,
                approval_roles=roles or [],
                tags=tags or ["approval", "governance"]
            )(fn)

        return decorator

    def input(
        self,
        name: str,
        type: Any = InputType.TEXT,
        default: Any = None,
        required: Optional[bool] = None,
        help_text: Optional[str] = None,
        options: Optional[List[str]] = None,
        sensitive: bool = False
    ) -> "FunctionalWorkflow":
        """Fluent helper to register an input parameter."""
        actual_type = InputType.TEXT
        if isinstance(type, InputType):
            actual_type = type
        elif type in (bool, "bool", "boolean", "checkbox"):
            actual_type = InputType.CHECKBOX
        elif type in (int, float, "int", "float", "number"):
            actual_type = InputType.NUMBER
        elif type in ("select", "SELECT") or options:
            actual_type = InputType.SELECT
        elif type in ("json", "JSON", dict, list):
            actual_type = InputType.JSON
        elif type in ("password", "PASSWORD"):
            actual_type = InputType.PASSWORD
        elif isinstance(type, str):
            try:
                actual_type = InputType(type.lower())
            except ValueError:
                actual_type = InputType.TEXT

        has_default = default is not None
        req = required if required is not None else (not has_default)

        field = InputField(
            name=name,
            type=actual_type,
            label=name.replace("_", " ").title(),
            default=default,
            required=req,
            help_text=help_text,
            options=options,
            sensitive=sensitive or (actual_type == InputType.PASSWORD)
        )
        self._custom_inputs.append(field)
        return self

    def profile(self, name: str, **kwargs) -> "FunctionalWorkflow":
        """Register a preset profile for this workflow."""
        self.profiles[name] = kwargs
        return self

    def get_steps(self) -> List[tuple[StepConfig, Callable]]:
        steps = list(self._steps)
        steps.sort(key=lambda s: (s[0].order, s[0].name))
        return steps

    def inputs(self) -> List[InputField]:
        if self._custom_inputs:
            return self._custom_inputs
        return self._infer_inputs_from_steps()

    def __call__(self, target: Optional[Any] = None) -> Any:
        """
        Enables using FunctionalWorkflow both as a decorator and as a factory:
        1. @workflow("name") class MyClass(Workflow) -> registers class and returns it
        2. wf() -> returns self (callable factory compatibility)
        """
        if target is None:
            return self

        if isinstance(target, type) and issubclass(target, Workflow):
            target.workflow_id = self.workflow_id
            if self.name and target.name == "Base Workflow":
                target.name = self.name
            if self.description:
                target.description = self.description
            if self.version:
                target.version = self.version
            if self.tags:
                target.tags = self.tags
            _GLOBAL_REGISTRY[self.workflow_id] = target
            return target

        if callable(target):
            # Target is a standalone function pipeline
            return self.step(target)

        return self


def workflow(
    name: Optional[Union[str, type, Callable]] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    version: str = "1.0.0",
    author: Optional[str] = None,
    profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    inputs: Optional[List[InputField]] = None,
    **kwargs
) -> Any:
    """
    Universal workflow decorator and factory:
    1. Decorate class: @workflow(name="...", description="...") class MyWorkflow(Workflow):
    2. Decorate class without args: @workflow class MyWorkflow(Workflow):
    3. Create functional workflow: wf = workflow("quick_deploy", description="...")
    """
    actual_name = name or kwargs.get("name")
    actual_desc = description or kwargs.get("description")
    actual_tags = tags or kwargs.get("tags")

    # Case 1: @workflow without parentheses on a class
    if isinstance(actual_name, type) and issubclass(actual_name, Workflow):
        wf_name = actual_name.__name__
        actual_name.workflow_id = wf_name
        _GLOBAL_REGISTRY[wf_name] = actual_name
        return actual_name

    # Case 2: Named workflow instance or decorator
    wf_name = actual_name if isinstance(actual_name, str) else "workflow"
    fw = FunctionalWorkflow(
        name=wf_name,
        description=actual_desc,
        version=version,
        tags=actual_tags,
        author=author,
        profiles=profiles,
        inputs=inputs
    )

    return fw
