"""
Workflows API endpoints.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ...core.registry import registry

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("", response_model=Dict[str, Any])
def list_all_workflows():
    """List all registered workflows, their metadata, and input schemas."""
    registry.discover()
    workflows = registry.list_workflows()
    return {
        "success": True,
        "count": len(workflows),
        "data": workflows
    }


@router.get("/{workflow_id}")
def get_workflow_schema(workflow_id: str):
    """Retrieve detailed schema and steps for a specific workflow."""
    registry.discover()
    workflows = registry.list_workflows()
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return {
        "success": True,
        "data": workflows[workflow_id]
    }
