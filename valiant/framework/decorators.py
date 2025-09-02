"""
Workflow step decorators and enhanced framework features for Phase 1 & 2 improvements.

This module provides decorator-based step registration, pre-built step templates,
and enhanced workflow development experience while maintaining full backward compatibility.
"""

import functools
import inspect
from typing import Dict, Any, Optional, List, Callable, Union, Tuple, Type
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time

from .engine import StepResult


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
    skip_on_failure: bool = False


class EnhancedStepResult:
    """Enhanced step result with additional metadata and utilities"""
    
    def __init__(self, name: str, success: bool = False, message: str = "", data: Any = None):
        self.name = name
        self._success = success
        self.message = message
        self.data = data if data is not None else {}
        self.skipped = False
        self.executed = True  # Set to True by default since we're creating a result
        self.time_taken = 0.0
        self.attempts = 1
        self.exception: Optional[Exception] = None
        self._step_config: Dict[str, Any] = {}
        self.derived_metrics: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.tags: List[str] = []
        print(f"[DEBUG] Created EnhancedStepResult for {name} with metrics={self.derived_metrics} tags={self.tags}")
    
    @property
    def success(self) -> bool:
        """Get the success status"""
        return self._success
    
    @success.setter
    def success(self, value: bool):
        """Set the success status"""
        self._success = value
    
    @classmethod
    def create_success(cls, name: str, message: str = "Step completed successfully", data: Any = None) -> 'EnhancedStepResult':
        """Create a successful step result"""
        result = cls(name, success=True, message=message, data=data)
        result.derived_metrics = {}  # Ensure metrics dict exists
        result.tags = []  # Ensure tags list exists
        return result
    
    @classmethod
    def create_failure(cls, name: str, message: str = "Step failed", data: Any = None, exception: Optional[Exception] = None) -> 'EnhancedStepResult':
        """Create a failed step result"""
        result = cls(name, success=False, message=message, data=data)
        result.exception = exception
        return result
    
    @classmethod
    def create_skip(cls, name: str, reason: str = "Step skipped") -> 'EnhancedStepResult':
        """Create a skipped step result"""
        result = cls(name, success=True, message=reason)
        result.skipped = True
        return result
    
    def add_metric(self, key: str, value: Any) -> 'EnhancedStepResult':
        """Add a derived metric/attribute to the result"""
        if not hasattr(self, 'derived_metrics'):
            self.derived_metrics = {}
        self.derived_metrics[key] = value
        print(f"[DEBUG] Added metric {key}={value} to {self.name}")  # Debug output
        return self
    
    def add_tag(self, tag: str) -> 'EnhancedStepResult':
        """Add a tag to the result"""
        if tag not in self.tags:
            self.tags.append(tag)
            print(f"[DEBUG] Tag added: {tag}")  # Debug statement
        return self
    
    def to_legacy_tuple(self) -> Tuple[bool, str, Any]:
        """Convert to legacy tuple format for backward compatibility"""
        return (self._success, self.message, self.data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step result to a dictionary including derived metrics and tags"""
        metrics = getattr(self, 'derived_metrics', {})
        tags = getattr(self, 'tags', [])
        print(f"[DEBUG] Step {self.name} has metrics: {metrics}")
        print(f"[DEBUG] Step {self.name} has tags: {tags}")
        
        result = {
            "name": self.name,
            "success": self._success,
            "message": self.message,
            "data": self.data,
            "derived_metrics": metrics,
            "tags": tags,
            "skipped": self.skipped,
            "executed": self.executed,
            "time_taken": self.time_taken,
            "attempts": self.attempts
        }
        return result


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
    skip_on_failure: bool = False
):
    """
    Decorator for workflow step methods.
    
    Automatically registers the method as a workflow step with the specified configuration.
    Supports both new EnhancedStepResult and legacy tuple return types.
    
    Args:
        name: Step name (defaults to method name)
        order: Execution order (lower numbers execute first)
        timeout: Step timeout in seconds
        retries: Number of retry attempts
        parallel_group: Group name for parallel execution
        requires: List of required context keys
        priority: Step priority level
        description: Step description for documentation
        tags: List of tags for categorization
        enabled: Whether the step is enabled
        skip_on_failure: Skip this step if previous steps failed
    
    Example:
        @step(name="Login", order=1, timeout=30, retries=2)
        def authenticate(self, context: Dict) -> EnhancedStepResult:
            return EnhancedStepResult.create_success("Login", "Authentication successful")
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
            skip_on_failure=skip_on_failure
        )
        
        func._step_config = config
        func._is_workflow_step = True
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                if isinstance(result, EnhancedStepResult):
                    # Store step configuration separately, not mixing with runtime metrics
                    result._step_config = {
                        "description": config.description,
                        "priority": config.priority.name,
                        "order": config.order,
                        "timeout": config.timeout,
                        "retries": config.retries,
                        "parallel_group": config.parallel_group
                    }
                    
                    # Add step configuration tags without duplicates
                    for t in config.tags:
                        result.add_tag(t)
                    return result
                elif isinstance(result, tuple) and len(result) == 3:
                    success, message, data = result
                    enhanced_result = EnhancedStepResult(step_name, success, message, data)
                    enhanced_result.derived_metrics = {}  # Initialize empty metrics dict
                    enhanced_result.tags = []  # Initialize empty tags list
                    enhanced_result._step_config.update({
                        "description": config.description,
                        "priority": config.priority.name,
                        "order": config.order,
                        "timeout": config.timeout,
                        "retries": config.retries,
                        "parallel_group": config.parallel_group
                    })
                    for t in config.tags:
                        enhanced_result.add_tag(t)
                    return enhanced_result
                else:
                    return EnhancedStepResult.create_failure(
                        step_name, 
                        f"Invalid return type from step: {type(result)}"
                    )
            except Exception as e:
                return EnhancedStepResult.create_failure(
                    step_name,
                    f"Step execution failed: {str(e)}",
                    exception=e
                )
        
        return wrapper
    
    return decorator


class StepTemplate:
    """Base class for pre-built step templates"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs
    
    def create_step_function(self) -> Callable:
        """Create the actual step function"""
        raise NotImplementedError("Subclasses must implement create_step_function")
    
    def validate_config(self) -> bool:
        """Validate the template configuration"""
        return True


class APIAuthStep(StepTemplate):
    """Pre-built template for API authentication steps"""
    
    def __init__(
        self,
        name: str = "API-Authentication",
        url: str = "/auth/login",
        username_field: str = "username",
        password_field: str = "password",
        token_extract: str = "token",
        store_as: str = "auth_token",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.url = url
        self.username_field = username_field
        self.password_field = password_field
        self.token_extract = token_extract
        self.store_as = store_as
        self.headers = headers or {}
        self.timeout = timeout
    
    def create_step_function(self) -> Callable:
        """Create API authentication step function"""
        from .utils import api_post, get_nested
        
        def auth_step(context: Dict) -> EnhancedStepResult:
            try:
                username = context.get(self.username_field)
                password = context.get(self.password_field)
                
                if not username or not password:
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"Missing credentials: {self.username_field} or {self.password_field}"
                    )
                
                auth_data = {
                    self.username_field: username,
                    self.password_field: password
                }
                
                success, response = api_post(
                    self.url,
                    context,
                    auth_data,
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if not success:
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"Authentication failed: {response}"
                    )
                
                token = get_nested(response, self.token_extract)
                if not token:
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"Token not found in response at path: {self.token_extract}"
                    )
                
                context[self.store_as] = token
                
                return EnhancedStepResult.create_success(
                    self.name,
                    f"Authentication successful for {username}",
                    {"token": token, "response": response}
                ).add_metric("auth_method", "api").add_tag("authentication")
                
            except Exception as e:
                return EnhancedStepResult.create_failure(
                    self.name,
                    f"Authentication error: {str(e)}",
                    exception=e
                )
        
        return auth_step


class APIGetStep(StepTemplate):
    """Pre-built template for API GET requests"""
    
    def __init__(
        self,
        name: str = "API-Get",
        url: str = "",
        requires_auth: bool = False,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer",
        auth_token_key: str = "auth_token",
        store_as: Optional[str] = None,
        validate: Optional[Dict[str, Any]] = None,
        extract: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.url = url
        self.requires_auth = requires_auth
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix
        self.auth_token_key = auth_token_key
        self.store_as = store_as
        self.validate = validate or {}
        self.extract = extract or {}
        self.headers = headers or {}
        self.timeout = timeout
    
    def create_step_function(self) -> Callable:
        """Create API GET step function"""
        from .utils import api_get, validate_response, get_nested
        
        def get_step(context: Dict) -> EnhancedStepResult:
            try:
                request_headers = self.headers.copy()
                
                if self.requires_auth:
                    token = context.get(self.auth_token_key)
                    if not token:
                        return EnhancedStepResult.create_failure(
                            self.name,
                            f"Authentication required but {self.auth_token_key} not found in context"
                        )
                    request_headers[self.auth_header] = f"{self.auth_prefix} {token}"
                
                success, response = api_get(
                    self.url,
                    context,
                    headers=request_headers,
                    timeout=self.timeout
                )
                
                if not success:
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"API request failed: {response}"
                    )
                
                if self.validate:
                    valid, message = validate_response(response, self.validate, context)
                    if not valid:
                        return EnhancedStepResult.create_failure(
                            self.name,
                            f"Response validation failed: {message}"
                        )
                
                extracted_data = {}
                for context_key, response_path in self.extract.items():
                    value = get_nested(response, response_path)
                    context[context_key] = value
                    extracted_data[context_key] = value
                
                if self.store_as:
                    context[self.store_as] = response
                
                return EnhancedStepResult.create_success(
                    self.name,
                    f"API request successful: {self.url}",
                    {"response": response, "extracted": extracted_data}
                ).add_metric("url", self.url).add_tag("api")
                
            except Exception as e:
                return EnhancedStepResult.create_failure(
                    self.name,
                    f"API request error: {str(e)}",
                    exception=e
                )
        
        return get_step


class CLIStep(StepTemplate):
    """Pre-built template for CLI command execution"""
    
    def __init__(
        self,
        name: str = "CLI-Command",
        command: str = "",
        capture_output: bool = True,
        extract_regex: Optional[str] = None,
        store_as: Optional[str] = None,
        fail_if: Optional[Callable[[str], bool]] = None,
        success_if: Optional[Callable[[str], bool]] = None,
        timeout: float = 30.0,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.command = command
        self.capture_output = capture_output
        self.extract_regex = extract_regex
        self.store_as = store_as
        self.fail_if = fail_if
        self.success_if = success_if
        self.timeout = timeout
    
    def create_step_function(self) -> Callable:
        """Create CLI command step function"""
        from .utils import run_cli
        import re
        
        def cli_step(context: Dict) -> EnhancedStepResult:
            try:
                success, output = run_cli(
                    context,
                    self.command,
                    capture_output=self.capture_output,
                    timeout=self.timeout
                )
                
                if not success:
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"Command failed: {output}"
                    )
                
                extracted_value = None
                if self.extract_regex and output:
                    match = re.search(self.extract_regex, output)
                    if match:
                        extracted_value = match.group(1) if match.groups() else match.group(0)
                        if self.store_as:
                            context[self.store_as] = extracted_value
                
                if self.fail_if and self.fail_if(output):
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"Command output failed validation: {output[:100]}..."
                    )
                
                if self.success_if and not self.success_if(output):
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"Command output did not meet success criteria: {output[:100]}..."
                    )
                
                return EnhancedStepResult.create_success(
                    self.name,
                    f"Command executed successfully: {self.command}",
                    {"output": output, "extracted": extracted_value}
                ).add_metric("command", self.command).add_tag("cli")
                
            except Exception as e:
                return EnhancedStepResult.create_failure(
                    self.name,
                    f"CLI command error: {str(e)}",
                    exception=e
                )
        
        return cli_step


class ValidationStep(StepTemplate):
    """Pre-built template for data validation steps"""
    
    def __init__(
        self,
        name: str = "Data-Validation",
        data_key: str = "",
        rules: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
        custom_validator: Optional[Callable[[Any], Tuple[bool, str]]] = None,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.data_key = data_key
        self.rules = rules or {}
        self.required_fields = required_fields or []
        self.custom_validator = custom_validator
    
    def create_step_function(self) -> Callable:
        """Create validation step function"""
        from .utils import validate_response, get_nested
        
        def validation_step(context: Dict) -> EnhancedStepResult:
            try:
                data = context.get(self.data_key)
                if data is None:
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"Data not found in context: {self.data_key}"
                    )
                
                missing_fields = []
                for field in self.required_fields:
                    if get_nested(data, field) is None:
                        missing_fields.append(field)
                
                if missing_fields:
                    return EnhancedStepResult.create_failure(
                        self.name,
                        f"Missing required fields: {', '.join(missing_fields)}"
                    )
                
                if self.rules:
                    valid, message = validate_response(data, self.rules)
                    if not valid:
                        return EnhancedStepResult.create_failure(
                            self.name,
                            f"Validation failed: {message}"
                        )
                
                if self.custom_validator:
                    valid, message = self.custom_validator(data)
                    if not valid:
                        return EnhancedStepResult.failure(
                            self.name,
                            f"Custom validation failed: {message}"
                        )
                
                return EnhancedStepResult.success(
                    self.name,
                    "Data validation passed",
                    {"validated_data": data}
                ).add_tag("validation")
                
            except Exception as e:
                return EnhancedStepResult.failure(
                    self.name,
                    f"Validation error: {str(e)}",
                    exception=e
                )
        
        return validation_step


def auto_discover_steps(workflow_instance) -> List[Tuple[StepConfig, Callable]]:
    """
    Automatically discover decorated step methods in a workflow instance.
    
    Returns a list of (StepConfig, function) tuples sorted by execution order.
    """
    steps = []
    
    for name in dir(workflow_instance):
        method = getattr(workflow_instance, name)
        
        if hasattr(method, '_is_workflow_step') and hasattr(method, '_step_config'):
            config = method._step_config
            steps.append((config, method))
    
    steps.sort(key=lambda x: (x[0].order, x[0].name))
    
    return steps


def register_template_steps(workflow_instance, templates: List[StepTemplate]) -> List[Tuple[StepConfig, Callable]]:
    """
    Register template-based steps in a workflow.
    
    Returns a list of (StepConfig, function) tuples for the template steps.
    """
    steps = []
    
    for template in templates:
        if not template.validate_config():
            raise ValueError(f"Invalid configuration for template: {template.name}")
        
        step_func = template.create_step_function()
        
        config = StepConfig(
            name=template.name,
            **template.config
        )
        
        steps.append((config, step_func))
    
    return steps
