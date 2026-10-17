"""
FastAPI router for inbound webhooks and webhook configuration management.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Header, Query, Request, status
from pydantic import BaseModel, Field

from ...core.registry import registry
from ...core.runner import WorkflowRunner
from ...db.database import (
    list_webhooks,
    get_webhook,
    get_webhook_by_token,
    create_webhook,
    update_webhook,
    delete_webhook,
    record_webhook_trigger,
    save_run_result,
    normalize_environment,
)

logger = logging.getLogger("valiant.webhooks")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class CreateWebhookRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    workflow_name: str
    token: Optional[str] = None
    environment: Optional[str] = None
    enabled: bool = True
    secret_header: Optional[str] = None
    parameter_mapping: Dict[str, Any] = Field(default_factory=dict)


class UpdateWebhookRequest(BaseModel):
    name: Optional[str] = None
    workflow_name: Optional[str] = None
    enabled: Optional[bool] = None
    secret_header: Optional[str] = None
    parameter_mapping: Optional[Dict[str, Any]] = None


async def _dispatch_webhook_workflow(webhook: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """Instantiate workflow and execute asynchronously with webhook payload."""
    wf_name = webhook["workflow_name"]
    env = webhook.get("environment") or "dev"
    hook_name = webhook.get("name") or "webhook"
    hook_id = webhook["id"]

    workflow_instance = registry.get_instance(wf_name)
    if not workflow_instance:
        raise ValueError(f"Workflow '{wf_name}' not found in registry")

    # Construct input parameters from mapping or raw payload
    inputs: Dict[str, Any] = {}
    mapping = webhook.get("parameter_mapping") or {}
    for param_name, payload_key in mapping.items():
        if payload_key in payload:
            inputs[param_name] = payload[payload_key]

    # If no mapping was defined, pass raw payload keys as inputs
    if not inputs and isinstance(payload, dict):
        inputs = dict(payload)

    # Always inject raw payload into context for advanced steps
    inputs["_webhook_payload"] = payload
    inputs["_webhook_id"] = hook_id

    runner = WorkflowRunner(
        workflow=workflow_instance,
        environment=env,
        profile=env,
        stop_on_failure=True
    )

    triggered_by = f"webhook: {hook_name}"
    record_webhook_trigger(hook_id, env=env)

    # Background execution
    async def _run_task():
        try:
            res = await runner.run(inputs)
            save_run_result(res, inputs, triggered_by=triggered_by, env=env)
        except Exception as e:
            logger.error("Error executing webhook run %s: %s", runner.run_id, e, exc_info=True)

    asyncio.create_task(_run_task())
    return runner.run_id


# ---------------------------------------------------------------------------
# Inbound Webhook Trigger Endpoint
# ---------------------------------------------------------------------------

@router.post("/{token}", status_code=status.HTTP_202_ACCEPTED)
async def handle_inbound_webhook(
    token: str,
    request: Request,
    x_valiant_secret: Optional[str] = Header(None, alias="X-Valiant-Secret"),
    authorization: Optional[str] = Header(None)
):
    """
    Public inbound receiver endpoint for external webhook events.
    Matches token across isolated databases, authenticates, and dispatches workflow.
    """
    hook = get_webhook_by_token(token)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found or invalid token")

    if not hook.get("enabled"):
        raise HTTPException(status_code=403, detail="Webhook is currently disabled")

    # Validate secret header if required
    required_secret = hook.get("secret_header")
    if required_secret:
        provided = x_valiant_secret or (authorization.replace("Bearer ", "") if authorization else None)
        if provided != required_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret token")

    # Ingest JSON payload safely
    try:
        body = await request.json()
    except Exception:
        body = {}

    run_id = await _dispatch_webhook_workflow(hook, body)

    return {
        "success": True,
        "message": f"Webhook '{hook['name']}' accepted for processing",
        "run_id": run_id,
        "workflow_name": hook["workflow_name"],
        "environment": hook.get("environment", "dev"),
        "status": "running"
    }


# ---------------------------------------------------------------------------
# Management Endpoints (CRUD)
# ---------------------------------------------------------------------------

@router.get("", response_model=Dict[str, Any])
def get_all_webhooks(
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    webhooks = list_webhooks(env=target_env)
    return {"success": True, "environment": target_env, "data": webhooks}


@router.post("", response_model=Dict[str, Any])
def create_new_webhook(
    payload: CreateWebhookRequest,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env")
):
    target_env = normalize_environment(payload.environment or x_valiant_env or "dev")

    if not registry.get(payload.workflow_name):
        raise HTTPException(status_code=400, detail=f"Workflow '{payload.workflow_name}' not found")

    hook_data = {
        "name": payload.name,
        "workflow_name": payload.workflow_name,
        "token": payload.token,
        "enabled": payload.enabled,
        "secret_header": payload.secret_header,
        "parameter_mapping": payload.parameter_mapping,
    }

    created = create_webhook(hook_data, env=target_env)
    return {"success": True, "data": created}


@router.get("/config/{webhook_id}", response_model=Dict[str, Any])
def get_single_webhook(
    webhook_id: str,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    hook = get_webhook(webhook_id, env=target_env)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"success": True, "data": hook}


@router.put("/config/{webhook_id}", response_model=Dict[str, Any])
def update_existing_webhook(
    webhook_id: str,
    payload: UpdateWebhookRequest,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    existing = get_webhook(webhook_id, env=target_env)
    if not existing:
        raise HTTPException(status_code=404, detail="Webhook not found")

    update_dict: Dict[str, Any] = {}
    if payload.name is not None:
        update_dict["name"] = payload.name
    if payload.workflow_name is not None:
        if not registry.get(payload.workflow_name):
            raise HTTPException(status_code=400, detail=f"Workflow '{payload.workflow_name}' not found")
        update_dict["workflow_name"] = payload.workflow_name
    if payload.enabled is not None:
        update_dict["enabled"] = payload.enabled
    if payload.secret_header is not None:
        update_dict["secret_header"] = payload.secret_header
    if payload.parameter_mapping is not None:
        update_dict["parameter_mapping"] = payload.parameter_mapping

    updated = update_webhook(webhook_id, update_dict, env=target_env)
    return {"success": True, "data": updated}


@router.post("/config/{webhook_id}/toggle", response_model=Dict[str, Any])
def toggle_webhook(
    webhook_id: str,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    existing = get_webhook(webhook_id, env=target_env)
    if not existing:
        raise HTTPException(status_code=404, detail="Webhook not found")

    new_state = not existing.get("enabled", True)
    updated = update_webhook(webhook_id, {"enabled": new_state}, env=target_env)
    return {"success": True, "data": updated}


@router.post("/config/{webhook_id}/test", response_model=Dict[str, Any])
async def test_webhook_ping(
    webhook_id: str,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    """Dispatch a test ping trigger directly from the UI."""
    target_env = normalize_environment(env or x_valiant_env or "dev")
    existing = get_webhook(webhook_id, env=target_env)
    if not existing:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_payload = {
        "event": "test.ping",
        "timestamp": "2026-10-11T21:45:00Z",
        "sender": "Valiant Automation UI Tester",
        "mock_value": 42
    }

    run_id = await _dispatch_webhook_workflow(existing, test_payload)
    return {
        "success": True,
        "message": f"Test ping dispatched for webhook '{existing['name']}'",
        "run_id": run_id,
        "environment": target_env
    }


@router.delete("/config/{webhook_id}", response_model=Dict[str, Any])
def delete_existing_webhook(
    webhook_id: str,
    x_valiant_env: Optional[str] = Header(None, alias="X-Valiant-Env"),
    env: Optional[str] = Query(None)
):
    target_env = normalize_environment(env or x_valiant_env or "dev")
    deleted = delete_webhook(webhook_id, env=target_env)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"success": True, "message": f"Webhook '{webhook_id}' deleted from {target_env}"}
