import os
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from ...core.registry import registry

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("", response_model=Dict[str, Any])
def list_all_workflows(include_defaults: bool = Query(True, description="Whether to include built-in default template workflows")):
    """List all registered workflows, their metadata, and input schemas."""
    registry.discover()
    hide_env = os.environ.get("VALIANT_HIDE_DEFAULTS", "0").lower() in ("1", "true", "yes")
    effective_include = include_defaults and not hide_env
    workflows = registry.list_workflows(include_defaults=effective_include)
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
