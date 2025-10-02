"""
Unified workflow registry supporting both explicit config and auto-discovery
"""
from typing import Dict, Optional
import importlib

def get_workflow_class_path(name: str) -> Optional[str]:
    """Get the full class path for a registered workflow"""
    # Try config first
    try:
        from valiant.workflows.config import get_all_workflows
        workflows = get_all_workflows()
        if name in workflows:
            if isinstance(workflows[name], str):
                return workflows[name]
            else:
                # Handle class objects from auto-discovery
                cls = workflows[name]
                return f"{cls.__module__}.{cls.__name__}"
    except ImportError:
        pass
    
    # Fallback to legacy config
    try:
        from valiant.workflows.config import WORKFLOWS
        return WORKFLOWS.get(name)
    except ImportError:
        return None

def get_available_workflows() -> Dict[str, str]:
    """Get all available workflows"""
    try:
        from valiant.workflows.config import get_all_workflows
        workflows = get_all_workflows()
        result = {}
        for name, workflow in workflows.items():
            if isinstance(workflow, str):
                result[name] = workflow
            else:
                # Handle class objects from auto-discovery
                result[name] = f"{workflow.__module__}.{workflow.__name__}"
        return result
    except ImportError:
        # Fallback to legacy config
        try:
            from valiant.workflows.config import WORKFLOWS
            return WORKFLOWS
        except ImportError:
            return {}
