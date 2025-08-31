"""
Enhanced workflow base class with decorator support and backward compatibility.

This module provides the new EnhancedBaseWorkflow class that supports decorator-based
step registration while maintaining full backward compatibility with existing workflows.
"""

from typing import Dict, List, Tuple, Any, Optional, Type, Union, Callable
from abc import ABC, abstractmethod
import inspect

from .workflow import BaseWorkflow, InputField
from .decorators import (
    auto_discover_steps, register_template_steps, StepTemplate, 
    EnhancedStepResult, StepConfig
)
from .engine import WorkflowRunner


class EnhancedBaseWorkflow(BaseWorkflow):
    """
    Enhanced base workflow class with decorator support and pre-built templates.
    
    Supports both new decorator-based step registration and legacy manual registration
    for full backward compatibility.
    
    Features:
    - Automatic step discovery via decorators
    - Pre-built step templates
    - Enhanced error handling and result types
    - Backward compatibility with existing workflows
    - Type-safe context management
    """
    
    def __init__(self, runner: Optional[WorkflowRunner] = None):
        """Initialize the enhanced workflow"""
        super().__init__()
        self.runner = runner
        self._step_templates: List[StepTemplate] = []
        self._auto_register_steps = True
        self._legacy_mode = False
    
    def add_template(self, template: StepTemplate) -> 'EnhancedBaseWorkflow':
        """
        Add a pre-built step template to the workflow.
        
        Args:
            template: The step template to add
            
        Returns:
            Self for method chaining
        """
        self._step_templates.append(template)
        return self
    
    def disable_auto_registration(self) -> 'EnhancedBaseWorkflow':
        """
        Disable automatic step discovery.
        Use this if you want to manually control step registration.
        
        Returns:
            Self for method chaining
        """
        self._auto_register_steps = False
        return self
    
    def enable_legacy_mode(self) -> 'EnhancedBaseWorkflow':
        """
        Enable legacy mode for backward compatibility.
        In legacy mode, only manual step registration is used.
        
        Returns:
            Self for method chaining
        """
        self._legacy_mode = True
        self._auto_register_steps = False
        return self
    
    def define_steps(self):
        """
        Enhanced step definition that supports both automatic discovery and manual registration.
        
        This method first attempts automatic step discovery, then falls back to manual
        registration for backward compatibility.
        """
        if not self.runner:
            raise RuntimeError("Workflow runner not initialized")
        
        steps_registered = False
        
        if self._auto_register_steps and not self._legacy_mode:
            discovered_steps = auto_discover_steps(self)
            if discovered_steps:
                for config, step_func in discovered_steps:
                    self._register_step_from_config(config, step_func)
                steps_registered = True
        
        if self._step_templates:
            template_steps = register_template_steps(self, self._step_templates)
            for config, step_func in template_steps:
                self._register_step_from_config(config, step_func)
            steps_registered = True
        
        if not steps_registered or self._legacy_mode:
            try:
                if hasattr(self, 'define_steps_manual'):
                    self.define_steps_manual()
                    steps_registered = True
            except (NotImplementedError, AttributeError):
                pass
        
        if not steps_registered and not self._legacy_mode:
            self._legacy_mode = True
            try:
                if hasattr(super(), 'define_steps'):
                    super().define_steps()
            except NotImplementedError:
                pass
    
    def define_steps_manual(self):
        """
        Override this method for manual step registration in enhanced workflows.
        This is called when auto-discovery doesn't find any decorated steps.
        """
        raise NotImplementedError(
            "Either use @step decorators on methods or override define_steps_manual()"
        )
    
    def _register_step_from_config(self, config: StepConfig, step_func: Callable):
        """Register a step with the runner using the step configuration"""
        if not config.enabled:
            return
        
        def step_wrapper(context: Dict) -> Tuple[bool, str, Any]:
            try:
                result = step_func(context)
                
                if isinstance(result, EnhancedStepResult):
                    return result.to_legacy_tuple()
                
                elif isinstance(result, tuple) and len(result) == 3:
                    return result
                
                else:
                    return False, f"Invalid return type from step {config.name}: {type(result)}", None
                    
            except Exception as e:
                return False, f"Step {config.name} failed with exception: {str(e)}", None
        
        if self.runner:
            self.runner.add_step(
                name=config.name,
                func=step_wrapper,
                requires=config.requires,
                parallel_group=config.parallel_group,
                timeout=config.timeout,
                retries=config.retries
            )
    
    def get_step_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata about all steps in the workflow.
        Useful for documentation and debugging.
        """
        metadata = {}
        
        if self._auto_register_steps:
            discovered_steps = auto_discover_steps(self)
            for config, step_func in discovered_steps:
                metadata[config.name] = {
                    "order": config.order,
                    "description": config.description,
                    "tags": config.tags,
                    "parallel_group": config.parallel_group,
                    "requires": config.requires,
                    "priority": config.priority.name,
                    "enabled": config.enabled,
                    "timeout": config.timeout,
                    "retries": config.retries,
                    "source": "decorator"
                }
        
        for template in self._step_templates:
            metadata[template.name] = {
                "description": f"Template step: {template.__class__.__name__}",
                "tags": ["template"],
                "config": template.config,
                "source": "template"
            }
        
        return metadata
    
    def validate_workflow(self) -> Tuple[bool, List[str]]:
        """
        Validate the workflow configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            discovered_steps = auto_discover_steps(self) if self._auto_register_steps else []
            template_steps = self._step_templates
            
            if not discovered_steps and not template_steps and not self._legacy_mode:
                errors.append("No steps defined in workflow")
            
            for config, _ in discovered_steps:
                if not config.name:
                    errors.append("Step has empty name")
                
                if config.timeout is not None and config.timeout <= 0:
                    errors.append(f"Step {config.name} has invalid timeout: {config.timeout}")
                
                if config.retries is not None and config.retries < 0:
                    errors.append(f"Step {config.name} has invalid retries: {config.retries}")
            
            for template in template_steps:
                if not template.validate_config():
                    errors.append(f"Template {template.name} has invalid configuration")
            
            step_names = [config.name for config, _ in discovered_steps]
            step_names.extend([template.name for template in template_steps])
            
            if len(step_names) != len(set(step_names)):
                duplicates = [name for name in step_names if step_names.count(name) > 1]
                errors.append(f"Duplicate step names found: {duplicates}")
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return len(errors) == 0, errors


class WorkflowBuilder:
    """
    Fluent builder for creating workflows with templates and decorators.
    
    Provides a convenient way to build workflows using method chaining.
    """
    
    def __init__(self, workflow_class: Type[EnhancedBaseWorkflow]):
        self.workflow_class = workflow_class
        self.templates: List[StepTemplate] = []
        self.config = {}
    
    def add_auth_step(
        self,
        name: str = "Authentication",
        url: str = "/auth/login",
        username_field: str = "username",
        password_field: str = "password",
        **kwargs
    ) -> 'WorkflowBuilder':
        """Add an API authentication step"""
        from .decorators import APIAuthStep
        
        template = APIAuthStep(
            name=name,
            url=url,
            username_field=username_field,
            password_field=password_field,
            **kwargs
        )
        self.templates.append(template)
        return self
    
    def add_api_get_step(
        self,
        name: str,
        url: str,
        requires_auth: bool = False,
        **kwargs
    ) -> 'WorkflowBuilder':
        """Add an API GET step"""
        from .decorators import APIGetStep
        
        template = APIGetStep(
            name=name,
            url=url,
            requires_auth=requires_auth,
            **kwargs
        )
        self.templates.append(template)
        return self
    
    def add_cli_step(
        self,
        name: str,
        command: str,
        **kwargs
    ) -> 'WorkflowBuilder':
        """Add a CLI command step"""
        from .decorators import CLIStep
        
        template = CLIStep(
            name=name,
            command=command,
            **kwargs
        )
        self.templates.append(template)
        return self
    
    def add_validation_step(
        self,
        name: str,
        data_key: str,
        **kwargs
    ) -> 'WorkflowBuilder':
        """Add a data validation step"""
        from .decorators import ValidationStep
        
        template = ValidationStep(
            name=name,
            data_key=data_key,
            **kwargs
        )
        self.templates.append(template)
        return self
    
    def build(self, runner: Optional[WorkflowRunner] = None) -> EnhancedBaseWorkflow:
        """Build the workflow instance"""
        workflow = self.workflow_class(runner)
        
        for template in self.templates:
            workflow.add_template(template)
        
        return workflow


LegacyBaseWorkflow = BaseWorkflow
