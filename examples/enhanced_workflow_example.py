"""
Example of an enhanced workflow using decorators and templates.

This example demonstrates the new Phase 1 & 2 features:
- Decorator-based step registration
- Pre-built step templates
- Enhanced error handling
- Backward compatibility
"""

from typing import Dict, List
from valiant.framework.enhanced_workflow import EnhancedBaseWorkflow, WorkflowBuilder
from valiant.framework.decorators import step, EnhancedStepResult, APIAuthStep, APIGetStep, CLIStep
from valiant.framework.workflow import InputField, InputType, WorkflowMetadata


class EnhancedAPIWorkflow(EnhancedBaseWorkflow):
    """
    Example enhanced workflow using decorators and templates.
    
    This workflow demonstrates:
    - Automatic step discovery via @step decorators
    - Pre-built step templates
    - Enhanced result types
    - Metadata and documentation
    """
    
    def __init__(self, runner=None):
        super().__init__(runner)
        
        metadata = WorkflowMetadata(
            name="Enhanced API Workflow",
            description="Demonstrates enhanced workflow features with decorators and templates",
            version="2.0.0",
            author="Valiant Framework",
            tags=["api", "authentication", "enhanced", "example"],
            category="examples",
            estimated_duration="2-3 minutes",
            complexity_level="medium"
        )
        self.set_metadata(metadata)
        
        self.add_template(APIAuthStep(
            name="API-Authentication",
            url="/auth/login",
            username_field="username",
            password_field="password",
            store_as="auth_token"
        ))
        
        self.add_template(APIGetStep(
            name="Get-User-Profile",
            url="/user/profile",
            requires_auth=True,
            store_as="user_profile",
            validate={"status": "active"},
            extract={"user_id": "id", "user_name": "name"}
        ))
        
        self.add_template(CLIStep(
            name="Check-System-Status",
            command="uptime",
            extract_regex=r"load average: ([\d.]+)",
            store_as="system_load"
        ))
    
    def _get_input_fields_impl(self) -> List[InputField]:
        """Define input fields using the new enhanced system"""
        return [
            InputField(
                name="username",
                type=InputType.TEXT,
                label="API Username",
                default="admin",
                help_text="Username for API authentication",
                validation_regex=r"^[a-zA-Z0-9_]{3,20}$",
                validation_message="Username must be 3-20 characters, alphanumeric and underscore only"
            ),
            InputField(
                name="password",
                type=InputType.PASSWORD,
                label="API Password",
                help_text="Password for API authentication"
            ),
            InputField(
                name="api_endpoint",
                type=InputType.TEXT,
                label="API Endpoint",
                default="https://api.example.com",
                help_text="Base URL for API endpoints",
                validation_regex=r"^https?://.*",
                validation_message="Must be a valid HTTP/HTTPS URL"
            ),
            InputField(
                name="timeout",
                type=InputType.NUMBER,
                label="Request Timeout",
                default=30,
                min_value=1,
                max_value=300,
                help_text="Request timeout in seconds"
            )
        ]
    
    @step(name="Initialize-Context", order=1, description="Initialize workflow context")
    def initialize_context(self, context: Dict) -> EnhancedStepResult:
        """Initialize the workflow context with default values"""
        try:
            context["base_url"] = context.get("api_endpoint", "https://api.example.com")
            context["headers"] = {
                "Content-Type": "application/json",
                "User-Agent": "Valiant-Workflow/2.0"
            }
            
            context["request_count"] = 0
            context["start_time"] = "2025-08-31T06:52:00Z"
            
            return EnhancedStepResult.create_success(
                "Initialize-Context",
                "Context initialized successfully",
                {"base_url": context["base_url"]}
            ).add_tag("setup").add_metric("initialization_time", "2025-08-31T06:52:00Z")
            
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Initialize-Context",
                f"Failed to initialize context: {str(e)}",
                exception=e
            )
    
    @step(name="Validate-Credentials", order=2, requires=["username", "password"])
    def validate_credentials(self, context: Dict) -> EnhancedStepResult:
        """Validate user credentials before proceeding"""
        try:
            username = context.get("username")
            password = context.get("password")
            
            if not username or len(username) < 3:
                return EnhancedStepResult.create_failure(
                    "Validate-Credentials",
                    "Username must be at least 3 characters long"
                )
            
            if not password or len(password) < 6:
                return EnhancedStepResult.create_failure(
                    "Validate-Credentials",
                    "Password must be at least 6 characters long"
                )
            
            if username == "admin" and password == "password123":
                return EnhancedStepResult.create_success(
                    "Validate-Credentials",
                    f"Credentials validated for user: {username}",
                    {"username": username, "validation_passed": True}
                ).add_tag("validation")
            else:
                return EnhancedStepResult.create_failure(
                    "Validate-Credentials",
                    "Invalid credentials provided"
                )
                
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Validate-Credentials",
                f"Credential validation error: {str(e)}",
                exception=e
            )
    
    @step(name="Process-User-Data", order=10, parallel_group="data_processing")
    def process_user_data(self, context: Dict) -> EnhancedStepResult:
        """Process user profile data"""
        try:
            user_profile = context.get("user_profile")
            if not user_profile:
                return EnhancedStepResult.create_skip(
                    "Process-User-Data",
                    "No user profile data available"
                )
            
            processed_data = {
                "user_id": user_profile.get("id"),
                "display_name": user_profile.get("name", "Unknown"),
                "account_status": user_profile.get("status", "inactive"),
                "last_login": "2025-08-31T06:52:00Z",
                "permissions": ["read", "write"]
            }
            
            context["processed_user_data"] = processed_data
            
            return EnhancedStepResult.create_success(
                "Process-User-Data",
                f"Processed data for user: {processed_data['display_name']}",
                processed_data
            ).add_metadata("processing_time", "0.5s").add_tag("processing")
            
            
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Process-User-Data",
                f"Data processing error: {str(e)}",
                exception=e
            )
    
    @step(name="Generate-Report", order=20, requires=["processed_user_data"])
    def generate_report(self, context: Dict) -> EnhancedStepResult:
        """Generate final workflow report"""
        try:
            processed_data = context.get("processed_user_data", {})
            system_load = context.get("system_load", "unknown")
            
            report = {
                "workflow_name": "Enhanced API Workflow",
                "execution_time": "2025-08-31T06:52:00Z",
                "user_info": {
                    "id": processed_data.get("user_id"),
                    "name": processed_data.get("display_name"),
                    "status": processed_data.get("account_status")
                },
                "system_info": {
                    "load_average": system_load
                },
                "summary": f"Successfully processed workflow for user {processed_data.get('display_name', 'Unknown')}",
                "recommendations": [
                    "User account is active and ready for use",
                    "System load is within normal parameters"
                ]
            }
            
            context["final_report"] = report
            
            return EnhancedStepResult.create_success(
                "Generate-Report",
                "Workflow report generated successfully",
                report
            ).add_tag("reporting").add_metric("report_size", len(str(report)))
            
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Generate-Report",
                f"Report generation error: {str(e)}",
                exception=e
            )


class LegacyCompatibilityWorkflow(EnhancedBaseWorkflow):
    """
    Example workflow demonstrating backward compatibility.
    
    This workflow uses the legacy manual step registration approach
    while still benefiting from enhanced features.
    """
    
    def __init__(self, runner=None):
        super().__init__(runner)
        self.enable_legacy_mode()
    
    def get_required_inputs(self) -> List[tuple]:
        """Legacy input definition method"""
        return [
            ("Enter username:", "username", False),
            ("Enter password:", "password", True),
            ("Enter API URL:", "api_url", False)
        ]
    
    def define_steps_manual(self):
        """Manual step registration (legacy approach)"""
        if not self.runner:
            return
        
        self.runner.add_step("Legacy-Step-1", self.step_one)
        self.runner.add_step("Legacy-Step-2", self.step_two)
        self.runner.add_step("Legacy-Step-3", self.step_three)
    
    def step_one(self, context: Dict) -> tuple:
        """Legacy step returning tuple format"""
        username = context.get("username", "unknown")
        return True, f"Legacy step 1 completed for {username}", {"step": 1}
    
    def step_two(self, context: Dict) -> tuple:
        """Legacy step returning tuple format"""
        return True, "Legacy step 2 completed", {"step": 2}
    
    def step_three(self, context: Dict) -> EnhancedStepResult:
        """Mixed approach: legacy registration with enhanced result"""
        return EnhancedStepResult.create_success(
            "Legacy-Step-3",
            "Legacy step 3 with enhanced result",
            {"step": 3, "enhanced": True}
        ).add_tag("legacy-enhanced")


def create_workflow_with_builder():
    """
    Example of using the WorkflowBuilder for fluent workflow creation.
    """
    builder = WorkflowBuilder(EnhancedBaseWorkflow)
    
    workflow = (builder
        .add_auth_step(
            name="Login",
            url="/auth/login",
            username_field="username",
            password_field="password"
        )
        .add_api_get_step(
            name="Get-Data",
            url="/api/data",
            requires_auth=True,
            store_as="api_data"
        )
        .add_cli_step(
            name="Check-Disk",
            command="df -h /",
            extract_regex=r"(\d+)%",
            store_as="disk_usage"
        )
        .add_validation_step(
            name="Validate-Data",
            data_key="api_data",
            required_fields=["id", "status"]
        )
        .build()
    )
    
    return workflow


if __name__ == "__main__":
    print("Enhanced Workflow Examples")
    print("=" * 50)
    
    enhanced_workflow = EnhancedAPIWorkflow()
    print(f"Enhanced Workflow: {enhanced_workflow.get_metadata().name}")
    print(f"Description: {enhanced_workflow.get_metadata().description}")
    print(f"Tags: {enhanced_workflow.get_tags()}")
    
    is_valid, errors = enhanced_workflow.validate_workflow()
    print(f"Validation: {'✓ Valid' if is_valid else '✗ Invalid'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
    
    step_metadata = enhanced_workflow.get_step_metadata()
    print(f"\nSteps ({len(step_metadata)}):")
    for step_name, metadata in step_metadata.items():
        print(f"  - {step_name}: {metadata.get('description', 'No description')}")
    
    print("\n" + "=" * 50)
    print("Legacy Compatibility Workflow")
    
    legacy_workflow = LegacyCompatibilityWorkflow()
    print(f"Legacy Workflow: {legacy_workflow.name}")
    
    print("\n" + "=" * 50)
    print("Builder Pattern Workflow")
    
    builder_workflow = create_workflow_with_builder()
    print(f"Builder Workflow: {builder_workflow.name}")
    
    print("\nAll examples completed successfully!")
