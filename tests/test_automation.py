"""
Unit and integration tests for P5: Scheduled Cron & Inbound Webhooks.
"""
import pytest
from fastapi.testclient import TestClient
from backend.valiant.api.app import app
from backend.valiant.core.cron_utils import (
    validate_cron_expression,
    compute_next_run_iso,
    get_human_description,
)
from backend.valiant.db.database import (
    create_schedule,
    get_schedule,
    delete_schedule,
    create_webhook,
    get_webhook,
    delete_webhook,
)


def test_cron_utils():
    # Valid crons
    valid, err = validate_cron_expression("*/5 * * * *")
    assert valid is True
    assert err is None

    valid, err = validate_cron_expression("@hourly")
    assert valid is True

    valid, err = validate_cron_expression("@every 10m")
    assert valid is True

    # Invalid cron
    valid, err = validate_cron_expression("not a cron")
    assert valid is False

    # Next run calculation
    next_iso = compute_next_run_iso("*/15 * * * *")
    assert next_iso is not None
    assert "T" in next_iso

    # Human description
    desc = get_human_description("*/5 * * * *")
    assert "5 minutes" in desc.lower()


def test_schedules_api_endpoints():
    with TestClient(app) as client:
        # 0. Test validate-cron
        val_res = client.post("/api/schedules/validate-cron", json={"cron_expression": "*/10 * * * *"})
        assert val_res.status_code == 200
        assert val_res.json()["valid"] is True
        assert "human_description" in val_res.json()

        # 1. Create a schedule
        payload = {
            "name": "Test Automation Audit",
            "workflow_name": "demo",
            "cron_expression": "0 * * * *",
            "inputs": {"max_items": 10},
            "enabled": True,
            "environment": "dev",
        }
        res = client.post("/api/schedules", json=payload, headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200
        data = res.json()["data"]
        sched_id = data["id"]
        assert data["name"] == "Test Automation Audit"
        assert data["workflow_name"] == "demo"
        assert data["next_run_at"] is not None

        # 2. List schedules
        res = client.get("/api/schedules", headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200
        schedules = res.json()["data"]
        assert any(s["id"] == sched_id for s in schedules)

        # 3. Toggle schedule
        res = client.post(f"/api/schedules/{sched_id}/toggle", headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200
        assert res.json()["data"]["enabled"] is False

        # 4. Trigger schedule now
        res = client.post(f"/api/schedules/{sched_id}/run", headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert "run_id" in res.json()

        # 5. Delete schedule
        res = client.delete(f"/api/schedules/{sched_id}", headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200


def test_webhooks_api_endpoints():
    with TestClient(app) as client:
        # 1. Create a webhook with secret
        payload = {
            "name": "GitHub CI Trigger",
            "workflow_name": "demo",
            "enabled": True,
            "secret_header": "test-secret-token-123",
            "parameter_mapping": {"user_name": "sender"},
            "environment": "dev",
        }
        res = client.post("/api/webhooks", json=payload, headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200
        data = res.json()["data"]
        hook_id = data["id"]
        token = data["token"]
        assert token is not None

        # 2. Inbound webhook call without required secret should fail (401)
        res = client.post(f"/api/webhooks/{token}", json={"sender": "Octocat"})
        assert res.status_code == 401

        # 3. Inbound webhook call with valid secret should succeed (202 Accepted)
        res = client.post(
            f"/api/webhooks/{token}",
            json={"sender": "Octocat", "event": "push"},
            headers={"X-Valiant-Secret": "test-secret-token-123"}
        )
        assert res.status_code == 202
        res_json = res.json()
        assert res_json["success"] is True
        assert "run_id" in res_json
        assert res_json["status"] == "running"

        # 4. Toggle webhook
        res = client.post(f"/api/webhooks/config/{hook_id}/toggle", headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200
        assert res.json()["data"]["enabled"] is False

        # 5. Disabled webhook should return 403
        res = client.post(
            f"/api/webhooks/{token}",
            json={"sender": "Octocat"},
            headers={"X-Valiant-Secret": "test-secret-token-123"}
        )
        assert res.status_code == 403

        # 6. Test ping endpoint
        res = client.post(f"/api/webhooks/config/{hook_id}/test", headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200
        assert res.json()["success"] is True

        # 7. Delete webhook
        res = client.delete(f"/api/webhooks/config/{hook_id}", headers={"X-Valiant-Env": "dev"})
        assert res.status_code == 200
