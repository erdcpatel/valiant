"""
Valiant Workflow Automation Platform
"""
__version__ = "0.0.3"

import sys

# Ensure both 'valiant' and 'valiantflow' resolve to this package module
sys.modules.setdefault("valiantflow", sys.modules[__name__])
sys.modules.setdefault("valiant", sys.modules[__name__])

from .core.models import (
    InputType,
    InputField,
    StepPriority,
    StepStatus,
    StepConfig,
    StepResult,
    WorkflowStatus,
    WorkflowResult,
    RunEvent,
    RunEventType,
)
from .core.context import WorkflowContext
from .core.workflow import Workflow, FunctionalWorkflow, step, workflow
from .core.runner import WorkflowRunner
from .core.registry import registry, WorkflowRegistry
from .tools.git import GitHelper
from .tools.maven import MavenHelper
from .tools.docker import DockerHelper

__all__ = [
    "__version__",
    "InputType",
    "InputField",
    "StepPriority",
    "StepStatus",
    "StepConfig",
    "StepResult",
    "WorkflowStatus",
    "WorkflowResult",
    "RunEvent",
    "RunEventType",
    "WorkflowContext",
    "Workflow",
    "FunctionalWorkflow",
    "step",
    "workflow",
    "WorkflowRunner",
    "registry",
    "WorkflowRegistry",
    "GitHelper",
    "MavenHelper",
    "DockerHelper",
]
