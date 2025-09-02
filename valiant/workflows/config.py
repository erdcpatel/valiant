"""
Workflow configuration - simple mapping of workflow names to class paths
"""
WORKFLOWS = {
    "api": "valiant.workflows.api_validation.workflow.APIValidationWorkflow",
    "system": "valiant.workflows.system_health.workflow.SystemHealthWorkflow",
    "user": "valiant.workflows.user_validation.workflow.UserValidationWorkflow",
    "enhanced_demo": "valiant.workflows.enhanced_demo.workflow.EnhancedDemoWorkflow",
    "test_basic": "valiant.workflows.test_basic.workflow.BasicDemoWorkflow"
}
