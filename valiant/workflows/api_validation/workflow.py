from typing import List

from valiant.framework.workflow import BaseWorkflow, InputField, InputType


class APIValidationWorkflow(BaseWorkflow):
    name = "API Validation Workflow"
    description = "Validates API endpoints with authentication"

    def __init__(self, runner=None):
        self.runner = runner

    def get_required_inputs(self) -> list:
        """For CLI compatibility: returns list of (prompt, key, is_secret) tuples."""
        fields = self.get_input_fields()
        return [
            (field.label, field.name, field.type == InputType.PASSWORD)
            for field in fields
        ]

    def get_input_fields(self) -> List[InputField]:
        return [
            InputField(
            name="env",
            type=InputType.SELECT,
            label="Environment",
            options=["dev", "staging", "prod"],
            default="dev",
            help_text="Choose the environment"
            ),
            InputField(
            name="start_date",
            type=InputType.DATE,
            label="Start Date",
            help_text="Pick a start date"
            ),
            InputField(
                name="username",
                type=InputType.TEXT,
                label="API Username",
                default="admin",
                help_text="Username for API authentication"
            ),
            InputField(
                name="password",
                type=InputType.PASSWORD,
                label="API Password",
                help_text="Password for API authentication"
            ),
            InputField(
                name="base_url",
                type=InputType.TEXT,
                label="Base URL",
                default="https://api.example.com",
                help_text="Base URL for API endpoints"
            ),
            InputField(
                name="timeout",
                type=InputType.NUMBER,
                label="Request Timeout",
                default=30,
                min_value=1,
                max_value=300,
                help_text="Request timeout in seconds"
            ),
            InputField(
                name="accept_terms",
                type=InputType.CHECKBOX,
                label="Accept Terms",
                default=False,
                help_text="You must accept terms to proceed"
            )
        ]

    def define_steps(self):
        self.runner.add_step("Login", self.step_login)
        # Add two parallel tasks in the "api_parallel" group
        self.runner.add_step("Get-Profile", self.step_get_profile, parallel_group="api_parallel")
        self.runner.add_step("Get-Settings", self.step_get_settings, parallel_group="api_parallel")
        self.runner.add_step("Validate-Data", self.step_validate_data)
        self.runner.add_step("Simulate-Failure", self.step_failure_example)

    def step_login(self, context: dict) -> tuple:
        username = context.get("username")
        password = context.get("password")
        # Simulate login logic
        return True, f"Login successful for {username}", None

    def step_get_profile(self, context: dict) -> tuple:
        # Simulate API call for profile
        return True, "Profile data retrieved", {"profile": {"name": "John Doe", "role": "admin"}}

    def step_get_settings(self, context: dict) -> tuple:
        # Simulate API call for settings
        return True, "Settings data retrieved", {"settings": {"theme": "dark", "notifications": True}}

    def step_validate_data(self, context: dict) -> tuple:
        # Simulate validation
        data = {
        "profile": {"name": "John Doe", "role": "admin"},
        "settings": {"theme": "dark", "notifications": True}
        }
        return True, "Data validation passed", data

    def step_failure_example(self, context: dict) -> tuple:
        # Simulate a failure scenario
        return False, "Simulated failure: Invalid API token", None