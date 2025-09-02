"""
Basic Demo Workflow - Minimal Example

This workflow demonstrates:
- Minimal step registration using @step
- Simple input schema
- Basic context usage and result reporting
"""

from typing import Dict, List, Tuple, Any
from valiant.framework.enhanced_workflow import EnhancedBaseWorkflow
from valiant.framework.decorators import step, EnhancedStepResult
from valiant.framework.workflow import InputField, InputType, WorkflowMetadata

class BasicDemoWorkflow(EnhancedBaseWorkflow):
    """
    Basic Demo Workflow showcasing minimal enhanced framework usage.
    """

    def get_metadata(self) -> WorkflowMetadata:
        return WorkflowMetadata(
            name="Basic Demo Workflow",
            description="A minimal workflow with two simple steps.",
            version="1.0.0",
            author="Valiant Enhanced Framework",
            category="demo",
            tags=["basic", "demo"],
            estimated_duration="10 seconds"
        )

    def get_required_inputs(self) -> List[Tuple[str, str, bool]]:
        fields = self._get_input_fields_impl()
        return [
            (field.label, field.name, field.type == InputType.PASSWORD)
            for field in fields
        ]

    def _get_input_fields_impl(self) -> List[InputField]:
        return [
            InputField(
                name="user_name",
                label="User Name",
                type=InputType.TEXT,
                required=True,
                default="Alice",
                help_text="Enter your name"
            ),
            InputField(
                name="favorite_number",
                label="Favorite Number",
                type=InputType.NUMBER,
                required=True,
                default=7,
                help_text="Enter your favorite number"
            )
        ]

    @step(
        name="Greet User",
        order=1,
        description="Greets the user by name.",
        tags=["greeting"],
        timeout=5
    )
    def greet_user(self, context: Dict) -> EnhancedStepResult:
        try:
            user_name = context.get("user_name", "User")
            greeting = f"Hello, {user_name}!"
            context["greeting"] = greeting
            return EnhancedStepResult.create_success(
                "Greet User",
                f"Greeting generated for {user_name}",
                {"greeting": greeting}
            )
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Greet User",
                f"Failed to greet user: {str(e)}",
                exception=e
            )

    @step(
        name="Process Number",
        order=2,
        description="Performs a simple calculation with the favorite number.",
        tags=["number", "calculation"],
        timeout=5
    )
    def process_number(self, context: Dict) -> EnhancedStepResult:
        try:
            number = int(context.get("favorite_number", 0))
            result = number * 2
            context["number_result"] = result
            return EnhancedStepResult.create_success(
                "Process Number",
                f"Processed number {number}, result is {result}",
                {"original": number, "doubled": result}
            )
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Process Number",
                f"Failed to process number: {str(e)}",
                exception=e
            )