"""
Simple workflow registry using explicit configuration
"""
from typing import Dict
import importlib

# Import the workflow configuration
try:
    from valiant.workflows.config import WORKFLOWS
except ImportError:
    # Fallback if config doesn't exist
    WORKFLOWS = {}

def get_workflow_class_path(name: str) -> str:
    """Get the full class path for a registered workflow"""
    return WORKFLOWS.get(name)

def get_available_workflows() -> Dict[str, str]:
    """Get all available workflows"""
    return WORKFLOWS