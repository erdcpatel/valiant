"""
Runs API endpoints for launching, tracking, smart-resuming, and canceling workflow executions.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, Query, Response
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uuid
import asyncio

from ...core.registry import registry
from ...core.runner import WorkflowRunner, _ACTIVE_RUNNERS
from ...core.models import RunEvent, StepResult, StepStatus
from ...core.environments import normalize_environment
from ...core.comparator import compare_runs_data
from ...db.database import (
    save_run_result,
    save_initial_run_record,
    get_recent_runs,
    get_run_by_id,
    delete_run_by_id,
    prune_run_history,
    clear_all_runs,
    update_step_approval
)
from .ws import ws_manager
from .auth import get_current_user

router = APIRouter(prefix="/runs", tags=["Runs"])


class ApproveStepRequest(BaseModel):
    notes: Optional[str] = None
    approver: Optional[str] = None


class RejectStepRequest(BaseModel):
    reason: Optional[str] = None
    approver: Optional[str] = None


def _build_active_runner_snapshot(runner: WorkflowRunner) -> Dict[str, Any]:
    step_dict_map = {s["name"]: dict(s) for s in getattr(runner, "initial_steps", [])}
    for res in getattr(runner, "step_results", []):
        step_dict_map[res.name] = res.model_dump()

    steps_list = list(step_dict_map.values())
    wf_name = getattr(runner.workflow, "workflow_id", runner.workflow.__class__.__name__)
    status = "running"
    if any(s.get("status") == "waiting_approval" for s in steps_list):
        status = "waiting_approval"
    return {
        "id": runner.run_id,
        "workflow_name": wf_name,
        "status": status,
        "success": False,
        "parent_run_id": runner.parent_run_id,
        "resumed_from_step": runner.resumed_from_step,
        "total_steps": len(steps_list),
        "executed_steps": len([s for s in steps_list if s.get("status") not in ["pending", "running"]]),
        "successful_steps": len([s for s in steps_list if s.get("status") == "success"]),
        "failed_steps": len([s for s in steps_list if s.get("status") == "failed"]),
        "skipped_steps": len([s for s in steps_list if s.get("status") == "skipped"]),
        "total_time": 0.0,
        "started_at": getattr(runner, "started_at", None),
        "completed_at": None,
        "inputs": getattr(runner, "inputs", {}),
        "context": runner.context.to_dict(mask_secrets=True) if hasattr(runner, "context") else {},
        "steps": steps_list,
        "error": None
    }


class TriggerRunRequest(BaseModel):
    workflow_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    run_id: Optional[str] = None
    async_mode: bool = False
    triggered_by: Optional[str] = None
    environment: Optional[str] = None
    profile: Optional[str] = None


class ResumeRunRequest(BaseModel):
    from_step: Optional[str] = None
    override_inputs: Optional[Dict[str, Any]] = None
    async_mode: bool = True
    triggered_by: Optional[str] = None
    environment: Optional[str] = None
    profile: Optional[str] = None


class CleanupRunsRequest(BaseModel):
    max_keep: int = 40
    days_retention: Optional[int] = None
    environment: Optional[str] = None


async def _execute_and_persist(runner: WorkflowRunner, inputs: Dict[str, Any], triggered_by: str, env: str = "dev"):
    run_id = runner.run_id
    _ACTIVE_RUNNERS[run_id] = runner
    try:
        result = await runner.run(inputs)
        save_run_result(result, inputs, triggered_by=triggered_by, env=env)
        return result
    finally:
        _ACTIVE_RUNNERS.pop(run_id, None)


@router.post("", response_model=Dict[str, Any])
async def trigger_run(
    payload: TriggerRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Trigger a workflow execution synchronously or asynchronously."""
    registry.discover()
    wf_class = registry.get(payload.workflow_name)
    if not wf_class:
        raise HTTPException(status_code=404, detail=f"Workflow '{payload.workflow_name}' not found")

    target_env = normalize_environment(payload.environment or request.headers.get("x-valiant-env"))
    target_profile = payload.profile or target_env
    run_id = payload.run_id or f"run_{uuid.uuid4().hex[:8]}"
    wf_instance = wf_class()

    # Determine actor (from auth cookie, bearer token, or payload override)
    triggered_by = payload.triggered_by or current_user.get("username", "anonymous")

    async def on_event_handler(event: RunEvent):
        await ws_manager.broadcast(run_id, event.model_dump())

    runner = WorkflowRunner(
        workflow=wf_instance,
        run_id=run_id,
        on_event=on_event_handler,
        environment=target_env,
        profile=target_profile
    )

    ordered_steps = wf_instance.get_steps()
    initial_steps = [
        {
            "name": cfg.name,
            "order": cfg.order,
            "tags": cfg.tags,
            "parallel_group": cfg.parallel_group,
            "requires": list(cfg.requires),
            "condition": cfg.condition,
            "status": "pending",
            "success": False,
            "reused": False,
            "skipped": False,
            "time_taken": 0.0,
            "message": "Waiting in queue"
        }
        for cfg, _ in ordered_steps
    ]
    runner.initial_steps = initial_steps
    save_initial_run_record(
        run_id=run_id,
        workflow_name=payload.workflow_name,
        inputs=payload.inputs,
        triggered_by=triggered_by,
        initial_steps=initial_steps,
        env=target_env,
        profile=target_profile
    )
    _ACTIVE_RUNNERS[run_id] = runner

    if payload.async_mode:
        asyncio.create_task(_execute_and_persist(runner, payload.inputs, triggered_by, target_env))
        return {
            "success": True,
            "run_id": run_id,
            "workflow_name": payload.workflow_name,
            "triggered_by": triggered_by,
            "environment": target_env,
            "profile": target_profile,
            "status": "running",
            "message": f"Workflow started in background [{target_env.upper()}]"
        }
    else:
        result = await _execute_and_persist(runner, payload.inputs, triggered_by, target_env)
        return {
            "success": result.success,
            "run_id": run_id,
            "workflow_name": payload.workflow_name,
            "triggered_by": triggered_by,
            "environment": target_env,
            "profile": target_profile,
            "status": result.status.value,
            "data": result.model_dump()
        }


@router.post("/{run_id}/resume", response_model=Dict[str, Any])
async def resume_run(
    run_id: str,
    payload: ResumeRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Smart Resume: Re-hydrate context from previous run, skip previously successful steps,
    and resume execution starting from the target step.
    """
    parent_data = get_run_by_id(run_id)
    if not parent_data:
        raise HTTPException(status_code=404, detail=f"Parent run '{run_id}' not found")

    target_env = normalize_environment(payload.environment or parent_data.get("environment") or request.headers.get("x-valiant-env"))
    target_profile = payload.profile or parent_data.get("profile") or target_env

    workflow_name = parent_data["workflow_name"]
    registry.discover()
    wf_class = registry.get(workflow_name)
    if not wf_class:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

    wf_instance = wf_class()
    ordered_steps = wf_instance.get_steps()
    step_names = [cfg.name for cfg, _ in ordered_steps]

    # Discover target step to resume from
    from_step = payload.from_step
    if not from_step:
        # Default: first failed or skipped step
        for s in parent_data.get("steps", []):
            if s.get("status") in ["failed", "skipped"]:
                from_step = s.get("name")
                break

    if not from_step:
        from_step = step_names[0] if step_names else ""

    if from_step not in step_names:
        raise HTTPException(status_code=400, detail=f"Step '{from_step}' not found in workflow '{workflow_name}'")

    target_idx = step_names.index(from_step)
    pre_seeded_context: Dict[str, Any] = {}
    reused_step_results: List[StepResult] = []
    parent_step_map = {s["name"]: s for s in parent_data.get("steps", [])}

    # Collect preceding successful step snapshots
    for i in range(target_idx):
        prev_name = step_names[i]
        if prev_name in parent_step_map:
            p_step = parent_step_map[prev_name]
            if p_step.get("status") == "success":
                if p_step.get("context_snapshot"):
                    pre_seeded_context.update(p_step["context_snapshot"])

                reused_step_results.append(
                    StepResult(
                        name=prev_name,
                        status=StepStatus.SUCCESS,
                        success=True,
                        message=p_step.get("message", "Completed"),
                        data=p_step.get("data"),
                        metrics=p_step.get("metrics", {}),
                        tags=p_step.get("tags", []),
                        logs=p_step.get("logs", []),
                        reused=True,
                        executed=True,
                        context_snapshot=p_step.get("context_snapshot")
                    )
                )

    # Fallback to parent overall context if individual snapshot was empty
    if not pre_seeded_context and parent_data.get("context"):
        pre_seeded_context = dict(parent_data["context"])

    # Merge inputs with optional user overrides
    inputs = dict(parent_data.get("inputs", {}))
    if payload.override_inputs:
        inputs.update(payload.override_inputs)

    new_run_id = f"run_res_{uuid.uuid4().hex[:8]}"
    triggered_by = payload.triggered_by or current_user.get("username", "anonymous")

    async def on_event_handler(event: RunEvent):
        await ws_manager.broadcast(new_run_id, event.model_dump())

    runner = WorkflowRunner(
        workflow=wf_instance,
        run_id=new_run_id,
        parent_run_id=run_id,
        resumed_from_step=from_step,
        on_event=on_event_handler,
        environment=target_env,
        profile=target_profile
    )

    async def _execute_resume():
        _ACTIVE_RUNNERS[new_run_id] = runner
        try:
            result = await runner.run(
                inputs=inputs,
                resume_from_step=from_step,
                pre_seeded_context=pre_seeded_context,
                reused_step_results=reused_step_results
            )
            save_run_result(result, inputs, triggered_by=triggered_by, env=target_env)
            return result
        finally:
            _ACTIVE_RUNNERS.pop(new_run_id, None)

    reused_names = {r.name: r for r in reused_step_results}
    initial_steps = []
    for cfg, _ in ordered_steps:
        if cfg.name in reused_names:
            prev = reused_names[cfg.name]
            initial_steps.append({
                "name": cfg.name,
                "order": cfg.order,
                "tags": cfg.tags,
                "parallel_group": cfg.parallel_group,
                "requires": list(cfg.requires),
                "condition": cfg.condition,
                "status": "success",
                "success": True,
                "reused": True,
                "skipped": False,
                "time_taken": 0.0,
                "message": f"[Reused from parent run] {prev.message or 'Completed'}",
                "context_snapshot": prev.context_snapshot or {}
            })
        else:
            initial_steps.append({
                "name": cfg.name,
                "order": cfg.order,
                "tags": cfg.tags,
                "parallel_group": cfg.parallel_group,
                "requires": list(cfg.requires),
                "condition": cfg.condition,
                "status": "pending",
                "success": False,
                "reused": False,
                "skipped": False,
                "time_taken": 0.0,
                "message": "Waiting in queue"
            })
    runner.initial_steps = initial_steps
    save_initial_run_record(
        run_id=new_run_id,
        workflow_name=workflow_name,
        inputs=inputs,
        triggered_by=triggered_by,
        initial_steps=initial_steps,
        parent_run_id=run_id,
        resumed_from_step=from_step,
        env=target_env,
        profile=target_profile
    )
    _ACTIVE_RUNNERS[new_run_id] = runner

    if payload.async_mode:
        asyncio.create_task(_execute_resume())
        return {
            "success": True,
            "run_id": new_run_id,
            "parent_run_id": run_id,
            "workflow_name": workflow_name,
            "resumed_from_step": from_step,
            "reused_steps_count": len(reused_step_results),
            "environment": target_env,
            "profile": target_profile,
            "status": "running",
            "message": f"Resumed workflow execution starting from '{from_step}' [{target_env.upper()}]"
        }
    else:
        result = await _execute_resume()
        return {
            "success": result.success,
            "run_id": new_run_id,
            "parent_run_id": run_id,
            "workflow_name": workflow_name,
            "resumed_from_step": from_step,
            "reused_steps_count": len(reused_step_results),
            "status": result.status.value,
            "data": result.model_dump()
        }


@router.post("/cleanup", response_model=Dict[str, Any])
def cleanup_history(
    request: Request,
    payload: CleanupRunsRequest = CleanupRunsRequest()
):
    """Prune historical runs to maintain compact database size and vacuum SQLite storage."""
    target_env = normalize_environment(payload.environment or request.headers.get("x-valiant-env"))
    count = prune_run_history(max_keep=payload.max_keep, days_retention=payload.days_retention, env=target_env)
    return {
        "success": True,
        "deleted_count": count,
        "environment": target_env,
        "message": f"Pruned {count} older runs and vacuumed SQLite storage [{target_env.upper()}]"
    }


@router.delete("", response_model=Dict[str, Any])
def clear_all_history(
    request: Request,
    env: Optional[str] = Query(None)
):
    """Clear all workflow run history and vacuum database for the specified environment."""
    target_env = normalize_environment(env or request.headers.get("x-valiant-env"))
    count = clear_all_runs(env=target_env)
    return {
        "success": True,
        "deleted_count": count,
        "environment": target_env,
        "message": f"Cleared {count} historical runs [{target_env.upper()}]"
    }


@router.get("", response_model=Dict[str, Any])
def list_run_history(
    request: Request,
    limit: int = 50,
    workflow_name: Optional[str] = None,
    user: Optional[str] = None,
    env: Optional[str] = Query(None)
):
    """Query recent workflow execution history filtered by isolated environment."""
    target_env = normalize_environment(env or request.headers.get("x-valiant-env"))
    runs = get_recent_runs(limit=limit, workflow_name=workflow_name, triggered_by=user, env=target_env)
    return {
        "success": True,
        "environment": target_env,
        "count": len(runs),
        "data": runs
    }


@router.get("/compare/diff", response_model=Dict[str, Any])
def compare_runs_endpoint(
    run_a: str = Query(..., description="Baseline run ID"),
    run_b: str = Query(..., description="Target run ID to compare"),
    env_a: Optional[str] = Query(None, description="Environment of baseline run"),
    env_b: Optional[str] = Query(None, description="Environment of target run"),
    request: Request = None,
):
    """Compare two workflow runs side-by-side to highlight latency drift and regressions."""
    data_a = get_run_by_id(run_a, env=normalize_environment(env_a) if env_a else None)
    if not data_a:
        raise HTTPException(status_code=404, detail=f"Baseline run '{run_a}' not found")

    data_b = get_run_by_id(run_b, env=normalize_environment(env_b) if env_b else None)
    if not data_b:
        raise HTTPException(status_code=404, detail=f"Target run '{run_b}' not found")

    diff_data = compare_runs_data(data_a, data_b)
    return {
        "success": True,
        "data": diff_data,
    }


@router.get("/{run_id}", response_model=Dict[str, Any])
def get_run_details(
    run_id: str,
    request: Request,
    env: Optional[str] = Query(None)
):
    """Retrieve full audit logs and step results for a specific run."""
    req_env = env or request.headers.get("x-valiant-env")
    run_data = get_run_by_id(run_id, env=normalize_environment(req_env) if req_env else None)
    runner = _ACTIVE_RUNNERS.get(run_id)

    if not run_data:
        if runner:
            return {
                "success": True,
                "data": _build_active_runner_snapshot(runner)
            }
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if runner and run_data.get("status") in ["running", "waiting_approval"]:
        live_snapshot = _build_active_runner_snapshot(runner)
        run_data["steps"] = live_snapshot["steps"]
        run_data["context"] = live_snapshot["context"]
        run_data["status"] = live_snapshot["status"]

    return {
        "success": True,
        "data": run_data
    }


@router.post("/{run_id}/cancel")
def cancel_active_run(run_id: str):
    """Cancel an active in-flight workflow run."""
    runner = _ACTIVE_RUNNERS.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail=f"Active run '{run_id}' not found or already completed")
    runner.cancel()
    return {
        "success": True,
        "run_id": run_id,
        "message": "Cancellation requested"
    }


@router.post("/{run_id}/steps/{step_name}/approve", response_model=Dict[str, Any])
async def approve_workflow_step(
    run_id: str,
    step_name: str,
    payload: ApproveStepRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    env: Optional[str] = Query(None)
):
    """
    Approve a suspended step execution.
    Signals the in-memory runner if active, or resumes execution persistently from SQLite.
    """
    approver = payload.approver or (current_user.get("name") if current_user else "Platform Operator")
    target_env = normalize_environment(env or request.headers.get("x-valiant-env") or "dev")

    from ...core.runner import signal_step_approval
    signaled = signal_step_approval(
        run_id=run_id,
        step_name=step_name,
        approved=True,
        approver=approver,
        notes=payload.notes
    )

    if signaled:
        update_step_approval(
            run_id=run_id,
            step_name=step_name,
            approved=True,
            approved_by=approver,
            notes=payload.notes,
            env=target_env
        )
        return {
            "success": True,
            "status": "approved",
            "mode": "live_event",
            "message": f"Step '{step_name}' approved by {approver}. Resuming execution."
        }

    # Fallback to persistent resumption from SQLite
    run_data = get_run_by_id(run_id, env=target_env)
    if not run_data:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    updated = update_step_approval(
        run_id=run_id,
        step_name=step_name,
        approved=True,
        approved_by=approver,
        notes=payload.notes,
        env=target_env
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Step '{step_name}' not found in run '{run_id}'")

    resume_payload = ResumeRunRequest(
        from_step=step_name,
        async_mode=True,
        triggered_by=approver,
        environment=target_env
    )
    res = await resume_run(run_id, resume_payload, request, background_tasks, current_user)
    return {
        "success": True,
        "status": "resumed",
        "mode": "persistent_resume",
        "new_run_id": res.get("run_id"),
        "message": f"Step '{step_name}' approved by {approver}. Execution resumed."
    }


@router.post("/{run_id}/steps/{step_name}/reject", response_model=Dict[str, Any])
async def reject_workflow_step(
    run_id: str,
    step_name: str,
    payload: RejectStepRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    env: Optional[str] = Query(None)
):
    """
    Reject a suspended step execution and abort downstream tasks.
    """
    approver = payload.approver or (current_user.get("name") if current_user else "Platform Operator")
    target_env = normalize_environment(env or request.headers.get("x-valiant-env") or "dev")

    from ...core.runner import signal_step_approval
    signaled = signal_step_approval(
        run_id=run_id,
        step_name=step_name,
        approved=False,
        approver=approver,
        notes=payload.reason
    )

    update_step_approval(
        run_id=run_id,
        step_name=step_name,
        approved=False,
        approved_by=approver,
        notes=payload.reason,
        env=target_env
    )

    return {
        "success": True,
        "status": "rejected",
        "message": f"Step '{step_name}' rejected by {approver}. Workflow halted."
    }


@router.delete("/{run_id}")
def delete_run(
    run_id: str,
    request: Request,
    env: Optional[str] = Query(None)
):
    """Delete a run record from history in the active environment."""
    req_env = env or request.headers.get("x-valiant-env")
    deleted = delete_run_by_id(run_id, env=normalize_environment(req_env) if req_env else None)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {
        "success": True,
        "run_id": run_id,
        "message": "Run deleted"
    }


@router.get("/{run_id}/steps/{step_name}/tabular/data", response_model=Dict[str, Any])
def get_tabular_data(
    run_id: str,
    step_name: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort_by: Optional[str] = Query(None),
    sort_desc: bool = Query(False),
    search: Optional[str] = Query(None),
    env: Optional[str] = Query(None)
):
    """
    Paginated query, search, and sorting of cached Polars Parquet dataset for a step.
    Executes in <5ms directly from memory-mapped Parquet scans.
    """
    from ...core.tabular import query_tabular_artifact
    target_env = normalize_environment(env or request.headers.get("x-valiant-env") or "dev")
    result = query_tabular_artifact(
        run_id=run_id,
        step_name=step_name,
        env=target_env,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_desc=sort_desc,
        search=search
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Dataset not found"))
    return result


@router.get("/{run_id}/steps/{step_name}/tabular/export")
def export_tabular_data(
    run_id: str,
    step_name: str,
    request: Request,
    format: str = Query("csv", pattern="^(csv|parquet|json)$"),
    env: Optional[str] = Query(None)
):
    """
    Stream full Polars dataset in CSV, Parquet, or JSON format for direct browser download.
    """
    from ...core.tabular import export_tabular_artifact
    target_env = normalize_environment(env or request.headers.get("x-valiant-env") or "dev")
    try:
        content_bytes, media_type, filename = export_tabular_artifact(
            run_id=run_id,
            step_name=step_name,
            env=target_env,
            format_type=format
        )
        return Response(
            content=content_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tabular dataset for step '{step_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export tabular dataset: {str(e)}")


@router.get("/{run_id}/report/html")
def get_run_html_report_endpoint(
    run_id: str,
    request: Request,
    download: bool = Query(False, description="Whether to trigger file download attachment"),
    env: Optional[str] = Query(None)
):
    """
    Generate and serve self-contained HTML execution report.
    Supports in-browser viewing, native print-to-PDF (@media print), and file download attachment.
    """
    from ...core.report import generate_run_html_report
    target_env = normalize_environment(env or request.headers.get("x-valiant-env") or "dev")
    run_data = get_run_by_id(run_id, env=target_env)
    runner = _ACTIVE_RUNNERS.get(run_id)

    if not run_data:
        if runner:
            run_data = _build_active_runner_snapshot(runner)
        else:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    elif runner and run_data.get("status") in ["running", "waiting_approval"]:
        live_snapshot = _build_active_runner_snapshot(runner)
        run_data["steps"] = live_snapshot["steps"]
        run_data["context"] = live_snapshot["context"]
        run_data["status"] = live_snapshot["status"]

    html_content = generate_run_html_report(run_data, env=target_env)

    headers = {"Content-Type": "text/html; charset=utf-8"}
    if download:
        filename = f"valiant-report-{run_id}-{target_env}.html"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return Response(content=html_content, media_type="text/html", headers=headers)


@router.get("/{run_id}/logs/file")
def get_run_log_file_endpoint(
    run_id: str,
    request: Request,
    download: bool = Query(False, description="Whether to trigger file download attachment"),
    env: Optional[str] = Query(None)
):
    """
    Retrieve or download dedicated per-run raw execution log (.log file).
    """
    from ...core.logging import RunLogManager
    target_env = normalize_environment(env or request.headers.get("x-valiant-env") or "dev")
    log_path = RunLogManager.get_path(run_id, env=target_env)

    if not log_path.exists():
        run_data = get_run_by_id(run_id, env=target_env)
        runner = _ACTIVE_RUNNERS.get(run_id)
        if not run_data and not runner:
            raise HTTPException(status_code=404, detail=f"Log file for run '{run_id}' not found")

    content = RunLogManager.read_log_content(run_id, env=target_env)

    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if download:
        filename = f"valiant-run-{run_id}-{target_env}.log"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return Response(content=content, media_type="text/plain", headers=headers)
