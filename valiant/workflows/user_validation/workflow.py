from typing import Dict, Tuple, List
from valiant.framework.workflow import BaseWorkflow, InputField, InputType
from valiant.framework.utils import api_get_and_process, log_response_summary, validate_response

class UserValidationWorkflow(BaseWorkflow):
    name = "User Data Validation Workflow"
    description = "Demonstrates API utilities with dummy data"

    def __init__(self, runner=None):
        self.runner = runner

    def get_input_fields(self) -> List[InputField]:
        return [
            InputField(
                name="user_id",
                type=InputType.NUMBER,
                label="User ID",
                default=42,
                help_text="ID of the user to validate"
            ),
            InputField(
                name="min_permissions",
                type=InputType.NUMBER,
                label="Minimum Permissions",
                default=3,
                min_value=1,
                max_value=10,
                help_text="Minimum number of permissions required"
            ),
            InputField(
                name="required_role",
                type=InputType.TEXT,
                label="Required Role",
                default="admin",
                help_text="Role required for validation"
            ),
            InputField(
                name="required_plan",
                type=InputType.TEXT,
                label="Required Subscription Plan",
                default="premium",
                help_text="Subscription plan required"
            ),
        ]

    def get_required_inputs(self) -> List[Tuple[str, str, bool]]:
        fields = self.get_input_fields()
        return [
            (field.label, field.name, field.type == InputType.PASSWORD)
            for field in fields
        ]

    def define_steps(self):
        self.runner.add_step("Get-User-Data", self.step_get_user_data)
        self.runner.add_step("Validate-Permissions", self.step_validate_permissions)
        self.runner.add_step("Log-Summary", self.step_log_summary)

    # Step 1: Get user data with validation and extraction
    def step_get_user_data(self, context: Dict) -> Tuple[bool, str, object]:
        # Simulate API response
        context["api_response"] = {
            "id": context.get("user_id", 42),
            "name": "John Doe",
            "status": "active",
            "role": "admin",
            "permissions": ["read", "write", "delete"],
            "subscription": {
                "status": "active",
                "plan": "premium"
            },
            "metadata": {
                "created": "2023-01-15",
                "logins": 127
            }
        }

        # Use api_get_and_process to validate and extract
        return api_get_and_process(
            url=f"/users/{context['api_response']['id']}",  # Not actually used in dummy
            context=context,
            checks={
                "status": "active",
                "permissions.length": lambda x: x >= context.get("min_permissions", 3)
            },
            set_values={
                "user_id": "id",
                "user_role": "role",
                "is_premium": "subscription.status",
                "login_count": "metadata.logins"
            }
        ) + (context["api_response"],) if len(api_get_and_process(
            url=f"/users/{context['api_response']['id']}",
            context=context,
            checks={
                "status": "active",
                "permissions.length": lambda x: x >= context.get("min_permissions", 3)
            },
            set_values={
                "user_id": "id",
                "user_role": "role",
                "is_premium": "subscription.status",
                "login_count": "metadata.logins"
            }
        )) == 2 else api_get_and_process(
            url=f"/users/{context['api_response']['id']}",
            context=context,
            checks={
                "status": "active",
                "permissions.length": lambda x: x >= context.get("min_permissions", 3)
            },
            set_values={
                "user_id": "id",
                "user_role": "role",
                "is_premium": "subscription.status",
                "login_count": "metadata.logins"
            }
        )

    # Step 2: Additional validation
    def step_validate_permissions(self, context: Dict) -> Tuple[bool, str, object]:
        # Directly use validate_response for custom validation
        valid, message = validate_response(
            response=context["api_response"],
            checks={
                "role": lambda r: r in [context.get("required_role", "admin"), "editor"],
                "subscription.plan": context.get("required_plan", "premium")
            }
        )

        if not valid:
            return False, message, None

        return True, "Permission validation passed", None

    # Step 3: Create summary
    def step_log_summary(self, context: Dict) -> Tuple[bool, str, object]:
        # Use log_response_summary to create meaningful output
        summary = log_response_summary(
            response=context["api_response"],
            keys=["id", "name", "role", "subscription.plan", "permissions.length"],
            prefix="User Summary: "
        )

        # Add custom context value
        context["summary"] = summary
        return True, summary, summary

    # Bonus: Step with failure simulation
    def step_failure_example(self, context: Dict) -> Tuple[bool, str, object]:
        # Simulate different response
        bad_response = {
            "id": 99,
            "name": "Test User",
            "status": "pending",
            "permissions": ["read"],
            "subscription": {"status": "expired"}
        }

        # This will fail validation
        result = api_get_and_process(
            url="/users/99",
            context=context,
            checks={
                "status": "active",
                "permissions.length": lambda x: x >= 2
            },
            set_values={
                "user_id": "id",
                "user_status": "status"
            }
        )
        if len(result) == 2:
            return result + (bad_response,)
        return