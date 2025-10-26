"""
Workflow configuration - simplified mapping using new unified framework
"""

# Simplified workflow registration using the new unified system
WORKFLOWS = {
    "demo": "valiant.workflows.demo.DemoWorkflow",
    "user_management": "valiant.workflows.user_management.UserManagementWorkflow",
    "investigate": "valiant.workflows.investigate.InvestigateWorkflow",
}

# Auto-discovery function for workflows using @workflow decorator
def discover_workflows():
    """Discover workflows registered with @workflow decorator"""
    from valiant import get_registered_workflows
    return get_registered_workflows()

def get_all_workflows():
    """Get all workflows from both config and auto-discovery"""
    workflows = WORKFLOWS.copy()
    workflows.update(discover_workflows())
    return workflows
