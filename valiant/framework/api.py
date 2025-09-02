"""
Direct API layer for programmatic workflow execution
"""
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from .engine import WorkflowRunner
from .registry import get_available_workflows
from .workflow import BaseWorkflow, InputType, InputField


class ValiantAPI:
    """Programmatic API for workflow execution"""

    @staticmethod
    def list_workflows() -> Dict[str, str]:
        """Get available workflows"""
        return get_available_workflows()

    @staticmethod
    async def run_workflow(
            workflow_name: str,
            environment: Optional[str] = None,
            timeout: float = 30.0,
            retries: int = 1,
            context_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a workflow programmatically"""
        # Get workflow class
        workflows = get_available_workflows()
        if workflow_name not in workflows:
            raise ValueError(f"Workflow not found: {workflow_name}")

        workflow_path = workflows[workflow_name]
        module_name, class_name = workflow_path.rsplit('.', 1)

        # Import workflow class
        module = __import__(module_name, fromlist=[class_name])
        workflow_class = getattr(module, class_name)

        # Initialize runner
        runner = WorkflowRunner(
            timeout=timeout,
            max_retries=retries,
            environment=environment,
            output_format="json"
        )

        # Add context overrides
        if context_overrides:
            runner.context.update(context_overrides)

        # Create workflow instance
        workflow = workflow_class(runner)

        # Get required inputs and provide empty values (UI will handle real inputs)
        for prompt, key, is_secret in workflow.get_required_inputs():
            if key not in runner.context:
                runner.context[key] = ""  # Placeholder, UI will provide real values

        # Setup and run workflow
        workflow.setup()
        workflow.define_steps()
        await runner.run()

        # Return results
        return {
            "success": all(r.success for r in runner.results if r.executed),
            "results": [
                {
                    "name": r.name,
                    "success": r.success,
                    "message": r.message,
                    "skipped": r.skipped,
                    "executed": r.executed,
                    "time_taken": round(r.time_taken, 2),
                    "attempts": r.attempts,
                    "data": r.data,
                    "derived_metrics": r.derived_metrics,  # Direct access
                    "tags": r.tags  # Direct access
                }
                for r in runner.results
            ],
            "context": runner.context,
            "summary": {
                "total_steps": len(runner.results),
                "executed_steps": sum(1 for r in runner.results if r.executed),
                "successful_steps": sum(1 for r in runner.results if r.success and r.executed),
                "skipped_steps": sum(1 for r in runner.results if r.skipped),
                "total_time": round(sum(r.time_taken for r in runner.results if r.executed), 2)
            }
        }

    @staticmethod
    def get_workflow_input_schema(workflow_name: str) -> List[Dict[str, Any]]:
        """Get input schema for a specific workflow with fallback"""
        try:
            workflows = ValiantAPI.list_workflows()
            if workflow_name not in workflows:
                raise ValueError(f"Workflow not found: {workflow_name}")

            workflow_path = workflows[workflow_name]
            module_name, class_name = workflow_path.rsplit('.', 1)

            # Import workflow class
            module = __import__(module_name, fromlist=[class_name])
            workflow_class = getattr(module, class_name)

            # Create instance
            workflow_instance = workflow_class(None)

            # Try to get input fields using new method
            try:
                input_fields = workflow_instance.get_input_fields()
            except (NotImplementedError, AttributeError):
                # Fallback to old method
                required_inputs = workflow_instance.get_required_inputs()
                input_fields = [
                    InputField(
                        name=key,
                        type=InputType.PASSWORD if is_secret else InputType.TEXT,
                        label=prompt.replace(':', '').strip(),
                        default=""
                    )
                    for prompt, key, is_secret in required_inputs
                ]

            # Convert to serializable format
            return [
                {
                    "name": field.name,
                    "type": field.type.value,
                    "label": field.label,
                    "required": field.required,
                    "default": field.default,
                    "help_text": field.help_text,
                    "options": field.options,
                    "min_value": field.min_value,
                    "max_value": field.max_value
                }
                for field in input_fields
            ]

        except Exception as e:
            raise ValueError(f"Failed to get input schema: {str(e)}")
