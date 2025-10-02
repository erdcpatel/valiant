"""
Unified Workflow Framework - Single, simplified workflow system for Valiant

This module provides a single, unified workflow system that replaces both
the legacy BaseWorkflow and EnhancedBaseWorkflow systems with a clean,
simple interface.
"""

from typing import Dict, List, Tuple, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import re
import inspect
import functools
from abc import ABC, abstractmethod


class InputType(Enum):
    """Input field types for workflow parameters"""
    TEXT = "text"
    PASSWORD = "password" 
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    DATE = "date"
    EMAIL = "email"
    CHECKBOX = "checkbox"


@dataclass
class InputField:
    """Input field definition for workflows"""
    name: str
    type: Union[InputType, str] = InputType.TEXT
    label: Optional[str] = None
    required: bool = True
    default: Any = None
    help_text: Optional[str] = None
    options: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    validation_regex: Optional[str] = None
    validation_message: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization to set defaults and convert types"""
        if self.label is None:
            self.label = self.name.replace('_', ' ').title()
        
        # Convert string types to enum
        if isinstance(self.type, str):
            self.type = InputType(self.type)
    
    def validate_value(self, value: Any) -> Tuple[bool, str]:
        """Validate a value against this field's constraints"""
        if self.required and (value is None or value == ""):
            return False, f"{self.label} is required"
        
        if value is None or value == "":
            return True, ""
        
        if self.type == InputType.NUMBER:
            try:
                num_value = float(value)
                if self.min_value is not None and num_value < self.min_value:
                    return False, f"{self.label} must be at least {self.min_value}"
                if self.max_value is not None and num_value > self.max_value:
                    return False, f"{self.label} must be at most {self.max_value}"
            except (ValueError, TypeError):
                return False, f"{self.label} must be a valid number"
        
        elif self.type == InputType.SELECT:
            if self.options and str(value) not in self.options:
                return False, f"{self.label} must be one of: {', '.join(self.options)}"
        
        elif self.type == InputType.EMAIL:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)):
                return False, f"{self.label} must be a valid email address"
        
        if self.validation_regex:
            if not re.match(self.validation_regex, str(value)):
                message = self.validation_message or f"{self.label} format is invalid"
                return False, message
        
        return True, ""


@dataclass
class StepResult:
    """Unified step result with simplified interface"""
    name: str
    success: bool = True
    message: str = ""
    data: Any = None
    skipped: bool = False
    executed: bool = True
    time_taken: float = 0.0
    attempts: int = 1
    exception: Optional[Exception] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_metric(self, key: str, value: Any) -> 'StepResult':
        """Add a metric to the result"""
        self.metrics[key] = value
        return self
    
    def add_tag(self, tag: str) -> 'StepResult':
        """Add a tag to the result"""
        if tag not in self.tags:
            self.tags.append(tag)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "name": self.name,
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "skipped": self.skipped,
            "executed": self.executed,
            "time_taken": self.time_taken,
            "attempts": self.attempts,
            "metrics": self.metrics,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    def to_legacy_tuple(self) -> Tuple[bool, str, Any]:
        """Convert to legacy tuple format for backward compatibility"""
        return (self.success, self.message, self.data)


class StepPriority(Enum):
    """Step execution priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass 
class StepConfig:
    """Configuration for a workflow step"""
    name: str
    order: int = 0
    timeout: Optional[float] = None
    retries: Optional[int] = None
    parallel_group: Optional[str] = None
    requires: List[str] = field(default_factory=list)
    priority: StepPriority = StepPriority.NORMAL
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    condition: Optional[str] = None


def step(
    name: Optional[str] = None,
    order: int = 0,
    timeout: Optional[float] = None,
    retries: Optional[int] = None,
    parallel_group: Optional[str] = None,
    requires: Optional[List[str]] = None,
    priority: StepPriority = StepPriority.NORMAL,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True,
    condition: Optional[str] = None
):
    """
    Decorator for workflow step methods.
    
    Args:
        name: Step name (defaults to method name)
        order: Execution order (lower numbers execute first)
        timeout: Step timeout in seconds
        retries: Number of retry attempts
        parallel_group: Group name for parallel execution
        requires: List of required context keys
        priority: Step priority level
        description: Step description
        tags: List of tags for categorization
        enabled: Whether the step is enabled
        condition: Context key that must be truthy to execute
    """
    def decorator(func: Callable) -> Callable:
        step_name = name or func.__name__.replace('_', '-').title()
        config = StepConfig(
            name=step_name,
            order=order,
            timeout=timeout,
            retries=retries,
            parallel_group=parallel_group,
            requires=requires or [],
            priority=priority,
            description=description or func.__doc__,
            tags=tags or [],
            enabled=enabled,
            condition=condition
        )
        
        func._step_config = config
        func._is_workflow_step = True
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # Handle different return types
                if isinstance(result, StepResult):
                    return result
                elif isinstance(result, tuple) and len(result) == 3:
                    success, message, data = result
                    return StepResult(step_name, success, message, data)
                else:
                    return StepResult(step_name, False, f"Invalid return type: {type(result)}")
                    
            except Exception as e:
                return StepResult(
                    step_name, 
                    success=False, 
                    message=f"Step execution failed: {str(e)}", 
                    exception=e
                )
        
        return wrapper
    
    return decorator


class Workflow:
    """
    Unified workflow base class.
    
    Provides a simple, clean interface for creating workflows with automatic
    step discovery and simplified result handling.
    """
    
    def __init__(self, runner=None):
        """Initialize the workflow"""
        self.runner = runner
        self.name = getattr(self.__class__, 'name', self.__class__.__name__)
        self.description = getattr(self.__class__, 'description', 'No description provided')
        self.version = getattr(self.__class__, 'version', '1.0.0')
        self.author = getattr(self.__class__, 'author', None)
        self.tags = getattr(self.__class__, 'tags', [])
        
    def inputs(self) -> List[InputField]:
        """
        Define input fields for this workflow.
        Override this method to specify required inputs.
        """
        return []
    
    def get_input_fields(self) -> List[InputField]:
        """Get input fields (compatibility method)"""
        return self.inputs()
    
    def get_required_inputs(self) -> List[Tuple[str, str, bool]]:
        """Get required inputs in legacy format for CLI compatibility"""
        input_fields = self.inputs()
        return [
            (field.label or field.name, field.name, field.type == InputType.PASSWORD)
            for field in input_fields
        ]
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate workflow inputs"""
        errors = []
        for field in self.inputs():
            value = inputs.get(field.name)
            is_valid, error_message = field.validate_value(value)
            if not is_valid:
                errors.append(error_message)
        return len(errors) == 0, errors
    
    def setup(self):
        """Setup workflow (called before execution)"""
        pass
    
    def define_steps(self):
        """Define workflow steps (auto-discovers decorated methods)"""
        if not self.runner:
            raise RuntimeError("Workflow runner not initialized")
        
        # Auto-discover decorated step methods
        steps = self._discover_steps()
        
        if not steps:
            raise NotImplementedError("No steps found. Use @step decorator on methods.")
        
        # Register steps with runner
        for config, step_func in steps:
            self._register_step(config, step_func)
    
    def _discover_steps(self) -> List[Tuple[StepConfig, Callable]]:
        """Discover decorated step methods"""
        steps = []
        
        for name in dir(self):
            method = getattr(self, name)
            if hasattr(method, '_is_workflow_step') and hasattr(method, '_step_config'):
                config = method._step_config
                steps.append((config, method))
        
        # Sort by order, then by name
        steps.sort(key=lambda x: (x[0].order, x[0].name))
        return steps
    
    def _register_step(self, config: StepConfig, step_func: Callable):
        """Register a step with the runner"""
        if not config.enabled:
            return
        
        def step_wrapper(context: Dict) -> Union[StepResult, Tuple[bool, str, Any]]:
            # Check condition if specified
            if config.condition and not context.get(config.condition):
                return StepResult(config.name, success=True, message="Step skipped due to condition", skipped=True)
            
            # Check required context keys
            missing_keys = [key for key in config.requires if key not in context]
            if missing_keys:
                return StepResult(
                    config.name,
                    success=False,
                    message=f"Missing required context keys: {', '.join(missing_keys)}"
                )
            
            try:
                result = step_func(context)
                
                if isinstance(result, StepResult):
                    # Add configuration tags
                    for tag in config.tags:
                        result.add_tag(tag)
                    
                    # Add metadata
                    result.metadata.update({
                        "step_priority": config.priority.name,
                        "step_order": config.order,
                        "step_description": config.description,
                        "timeout": config.timeout,
                        "retries": config.retries,
                        "parallel_group": config.parallel_group
                    })
                    
                    return result
                
                elif isinstance(result, tuple) and len(result) == 3:
                    success, message, data = result
                    step_result = StepResult(config.name, success, message, data)
                    for tag in config.tags:
                        step_result.add_tag(tag)
                    return step_result
                
                else:
                    return StepResult(
                        config.name,
                        success=False,
                        message=f"Invalid return type from step: {type(result)}"
                    )
                    
            except Exception as e:
                return StepResult(
                    config.name,
                    success=False,
                    message=f"Step failed with exception: {str(e)}",
                    exception=e
                )
        
        if self.runner:
            self.runner.add_step(
                name=config.name,
                func=step_wrapper,
                requires=config.requires,
                parallel_group=config.parallel_group,
                timeout=config.timeout,
                retries=config.retries
            )
    
    def success(self, message: str, data: Any = None) -> StepResult:
        """Create a successful step result"""
        return StepResult(name="", success=True, message=message, data=data)
    
    def failure(self, message: str, data: Any = None, error: Optional[Exception] = None) -> StepResult:
        """Create a failed step result"""
        return StepResult(name="", success=False, message=message, data=data, exception=error)
    
    def skip(self, message: str = "Step skipped") -> StepResult:
        """Create a skipped step result"""
        return StepResult(name="", success=True, message=message, skipped=True)
    
    def run(self, context: Optional[Dict[str, Any]] = None):
        """Run the workflow with given context"""
        import asyncio
        from .engine import WorkflowRunner
        
        if context is None:
            context = {}
        
        # Create runner if not provided
        if not self.runner:
            self.runner = WorkflowRunner()
        
        # Set context
        self.runner.context.update(context)
        
        # Setup and run
        self.setup()
        self.define_steps()
        asyncio.run(self.runner.run())
        
        return self.runner.results


# Registry for auto-discovery
_workflow_registry = {}

def register_workflow(name: str, workflow_class: type):
    """Register a workflow for auto-discovery"""
    _workflow_registry[name] = workflow_class

def workflow(name: str):
    """Decorator to auto-register workflows"""
    def decorator(cls):
        register_workflow(name, cls)
        return cls
    return decorator

def get_registered_workflows() -> Dict[str, type]:
    """Get all registered workflows"""
    return _workflow_registry.copy()