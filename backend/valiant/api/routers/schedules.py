"""
FastAPI router for managing scheduled cron triggers.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field

from ...core.scheduler import scheduler
from ...core.cron_utils import validate_cron_expression, compute_next_run_iso, get_human_description
from ...core.registry import registry
from ...db.database import (
    list_schedules,
    get_schedule,
    create_schedule,
    update_schedule,
    delete_schedule,
    normalize_environment,
)

router = APIRouter(prefix="/schedules", tags=["Schedules"])


class CreateScheduleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    workflow_name: str
    cron_expression: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    environment: Optional[str] = None


class UpdateScheduleRequest(BaseModel):
    name: Optional[str] = None
    workflow_name: Optional[str] = None
    cron_expression: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class ValidateCronRequest(BaseModel):
    cron_expression: str


@router.get("", response_model=Dict[str, Any])
def get_all_schedules(
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    schedules = list_schedules(env=target_env)
    for s in schedules:
        s["human_description"] = get_human_description(s.get("cron_expression", ""))
    return {"success": True, "environment": target_env, "data": schedules}


@router.post("", response_model=Dict[str, Any])
def create_new_schedule(
    payload: CreateScheduleRequest,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env")
):
    target_env = normalize_environment(payload.environment or x_valiant_env or "dev")

    # Validate workflow exists
    if not registry.get(payload.workflow_name):
        raise HTTPException(status_code=400, detail=f"Workflow '{payload.workflow_name}' not found")

    # Validate cron syntax
    valid, err = validate_cron_expression(payload.cron_expression)
    if not valid:
        raise HTTPException(status_code=400, detail=err or "Invalid cron expression")

    # Calculate initial next_run_at
    next_run = compute_next_run_iso(payload.cron_expression) if payload.enabled else None

    schedule_data = {
        "name": payload.name,
        "workflow_name": payload.workflow_name,
        "cron_expression": payload.cron_expression.strip(),
        "inputs": payload.inputs,
        "enabled": payload.enabled,
        "next_run_at": next_run,
    }

    created = create_schedule(schedule_data, env=target_env)
    created["human_description"] = get_human_description(created.get("cron_expression", ""))
    return {"success": True, "data": created}


@router.post("/validate-cron", response_model=Dict[str, Any])
def validate_cron_endpoint(payload: ValidateCronRequest):
    valid, err = validate_cron_expression(payload.cron_expression)
    if not valid:
        return {"valid": False, "error": err}
    desc = get_human_description(payload.cron_expression)
    next_iso = compute_next_run_iso(payload.cron_expression)
    return {
        "valid": True,
        "human_description": desc,
        "next_runs": [next_iso] if next_iso else []
    }


@router.get("/{schedule_id}", response_model=Dict[str, Any])
def get_single_schedule(
    schedule_id: str,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    sched = get_schedule(schedule_id, env=target_env)
    if not sched:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found in {target_env}")
    sched["human_description"] = get_human_description(sched.get("cron_expression", ""))
    return {"success": True, "data": sched}


@router.put("/{schedule_id}", response_model=Dict[str, Any])
def update_existing_schedule(
    schedule_id: str,
    payload: UpdateScheduleRequest,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    existing = get_schedule(schedule_id, env=target_env)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_dict: Dict[str, Any] = {}
    if payload.name is not None:
        update_dict["name"] = payload.name
    if payload.workflow_name is not None:
        if not registry.get(payload.workflow_name):
            raise HTTPException(status_code=400, detail=f"Workflow '{payload.workflow_name}' not found")
        update_dict["workflow_name"] = payload.workflow_name
    if payload.inputs is not None:
        update_dict["inputs"] = payload.inputs
    if payload.enabled is not None:
        update_dict["enabled"] = payload.enabled

    if payload.cron_expression is not None:
        valid, err = validate_cron_expression(payload.cron_expression)
        if not valid:
            raise HTTPException(status_code=400, detail=err or "Invalid cron expression")
        update_dict["cron_expression"] = payload.cron_expression.strip()
        is_enabled = payload.enabled if payload.enabled is not None else existing.get("enabled", True)
        if is_enabled:
            update_dict["next_run_at"] = compute_next_run_iso(payload.cron_expression.strip())
        else:
            update_dict["next_run_at"] = None
    elif payload.enabled is not None:
        if payload.enabled:
            update_dict["next_run_at"] = compute_next_run_iso(existing.get("cron_expression", ""))
        else:
            update_dict["next_run_at"] = None

    updated = update_schedule(schedule_id, update_dict, env=target_env)
    if updated:
        updated["human_description"] = get_human_description(updated.get("cron_expression", ""))
    return {"success": True, "data": updated}


@router.post("/{schedule_id}/toggle", response_model=Dict[str, Any])
def toggle_schedule(
    schedule_id: str,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    existing = get_schedule(schedule_id, env=target_env)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule not found")

    new_state = not existing.get("enabled", True)
    next_run = compute_next_run_iso(existing.get("cron_expression", "")) if new_state else None

    updated = update_schedule(
        schedule_id,
        {"enabled": new_state, "next_run_at": next_run},
        env=target_env
    )
    return {"success": True, "data": updated}


@router.post("/{schedule_id}/run", response_model=Dict[str, Any])
async def run_schedule_now(
    schedule_id: str,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    existing = get_schedule(schedule_id, env=target_env)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule not found")

    run_id = await scheduler.trigger_now(schedule_id, env=target_env)
    if not run_id:
        raise HTTPException(status_code=500, detail="Failed to trigger scheduled run")

    return {
        "success": True,
        "run_id": run_id,
        "message": f"Successfully triggered schedule '{existing['name']}'",
        "environment": target_env
    }


@router.delete("/{schedule_id}", response_model=Dict[str, Any])
def delete_existing_schedule(
    schedule_id: str,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    deleted = delete_schedule(schedule_id, env=target_env)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"success": True, "message": f"Schedule '{schedule_id}' deleted from {target_env}"}
