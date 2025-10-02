"""
Valiant Workflow Automation Platform

A flexible platform for creating, managing, and executing automated workflows
with support for validation, orchestration, and monitoring.
"""

__version__ = "2.0.0"
__author__ = "Valiant Team"

# Single import strategy - expose all key components
from .framework.workflow_unified import (
    Workflow,
    step,
    InputField,
    InputType,
    StepResult,
    StepPriority,
    workflow,
    register_workflow,
    get_registered_workflows
)

# Backward compatibility exports
from .framework.engine import WorkflowRunner

__all__ = [
    'Workflow',
    'step', 
    'InputField',
    'InputType',
    'StepResult',
    'StepPriority',
    'workflow',
    'register_workflow',
    'get_registered_workflows',
    'WorkflowRunner'
]