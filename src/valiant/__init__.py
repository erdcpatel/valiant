"""
Valiant Workflow Automation Platform v3

Public API — everything a workflow developer needs::

    from valiant import Workflow, step, workflow, InputField, InputType, StepResult

Example::

    from valiant import Workflow, step, workflow, InputField, InputType

    @workflow(name="greet", description="Greets a user")
    class GreetWorkflow(Workflow):

        def get_input_fields(self):
            return [InputField(name="name", required=True)]

        @step(name="Greet", order=1)
        def greet(self, ctx):
            return self.success(f"Hello, {ctx['name']}!", metrics={"length": len(ctx['name'])})
"""

__version__ = "3.0.0"

from valiant.core.context import WorkflowContext
from valiant.core.models import InputField, InputType, StepResult, WorkflowMeta, WorkflowResult
from valiant.core.registry import WorkflowRegistry, registry
from valiant.core.runner import WorkflowRunner
from valiant.core.workflow import Workflow, step, workflow

__all__ = [
    "__version__",
    "Workflow",
    "WorkflowContext",
    "WorkflowMeta",
    "WorkflowResult",
    "WorkflowRunner",
    "WorkflowRegistry",
    "registry",
    "step",
    "workflow",
    "InputField",
    "InputType",
    "StepResult",
]
