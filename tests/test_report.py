import os
import pytest
from fastapi.testclient import TestClient

from backend.valiant.core.report import generate_run_html_report
from backend.valiant.api.app import app
from backend.valiant.db.database import save_initial_run_record, save_run_result, init_db


@pytest.fixture(autouse=True)
def ensure_db():
    init_db("dev")


def test_generate_run_html_report_basic():
    run_data = {
        "id": "run_test_report_123",
        "workflow_name": "Test Workflow",
        "status": "completed",
        "success": True,
        "total_steps": 3,
        "successful_steps": 3,
        "failed_steps": 0,
        "skipped_steps": 0,
        "total_time": 1.25,
        "started_at": "2026-10-11T12:00:00",
        "completed_at": "2026-10-11T12:00:01",
        "triggered_by": "test_operator",
        "inputs": {"batch_size": 50},
        "steps": [
            {
                "name": "Step 1: Init",
                "order": 1,
                "status": "success",
                "success": True,
                "execution_time": 0.25,
                "message": "Initialized successfully",
                "metrics": {"records": 50},
            },
            {
                "name": "Step 2: Process",
                "order": 2,
                "status": "success",
                "success": True,
                "execution_time": 1.0,
                "message": "Processed 50 items",
            }
        ]
    }

    html = generate_run_html_report(run_data, env="dev")
    assert "<!DOCTYPE html>" in html
    assert "run_test_report_123" in html
    assert "Test Workflow" in html
    assert "DEV" in html
    assert "COMPLETED" in html
    assert "@media print" in html
    assert "Step 1: Init" in html
    assert "Step 2: Process" in html
    assert "test_operator" in html


def test_generate_run_html_report_with_approval_and_tabular():
    run_data = {
        "id": "run_approval_tabular",
        "workflow_name": "Prod Deploy & Analytics",
        "status": "completed",
        "success": True,
        "total_steps": 2,
        "successful_steps": 2,
        "failed_steps": 0,
        "skipped_steps": 0,
        "total_time": 4.5,
        "started_at": "2026-10-11T14:00:00",
        "completed_at": "2026-10-11T14:00:04",
        "triggered_by": "lead_eng",
        "inputs": {"env": "prod"},
        "steps": [
            {
                "name": "Manual Approval Gate",
                "order": 1,
                "status": "success",
                "success": True,
                "execution_time": 0.1,
                "requires_approval": True,
                "approval_prompt": "Approve production deployment gate",
                "approved_by": "lead_eng",
                "approval_notes": "Approved after QA signoff",
                "approved_at": "2026-10-11T14:00:02",
            },
            {
                "name": "SQL Query Step",
                "order": 2,
                "status": "success",
                "success": True,
                "execution_time": 0.8,
                "tabular_data": {
                    "total_rows": 3,
                    "total_cols": 2,
                    "columns": [
                        {"name": "id", "type": "i64", "category": "integer"},
                        {"name": "status", "type": "str", "category": "string"},
                    ],
                    "preview_rows": [
                        {"id": 1, "status": "active"},
                        {"id": 2, "status": "pending"},
                        {"id": 3, "status": "active"},
                    ]
                }
            }
        ]
    }

    html = generate_run_html_report(run_data, env="prod")
    assert "run_approval_tabular" in html
    assert "PROD" in html
    assert "Human-in-the-Loop Gate" in html
    assert "Approved after QA signoff" in html
    assert "lead_eng" in html
    assert "Polars Tabular Dataset" in html
    assert "active" in html
    assert "pending" in html


def test_generate_run_html_report_failed():
    run_data = {
        "id": "run_failed_report",
        "workflow_name": "Failed Pipeline",
        "status": "failed",
        "success": False,
        "total_steps": 2,
        "successful_steps": 1,
        "failed_steps": 1,
        "skipped_steps": 0,
        "total_time": 0.5,
        "steps": [
            {
                "name": "Step 1",
                "status": "success",
                "success": True,
                "execution_time": 0.2,
            },
            {
                "name": "Step 2",
                "status": "failed",
                "success": False,
                "execution_time": 0.3,
                "error": "ConnectionRefusedError: Database host unreachable at port 5432",
            }
        ]
    }

    html = generate_run_html_report(run_data, env="dev")
    assert "FAILED" in html
    assert "ConnectionRefusedError" in html
    assert "Database host unreachable" in html


def test_api_html_report_endpoint():
    client = TestClient(app)

    # Save a run to DB
    run_id = "run_api_test_report_999"
    save_initial_run_record(
        run_id=run_id,
        workflow_name="API Test Workflow",
        inputs={"foo": "bar"},
        triggered_by="tester",
        env="dev",
        initial_steps=[{"name": "Step 1", "order": 1, "status": "success"}]
    )

    # 1. Fetch inline HTML report
    res = client.get(f"/api/runs/{run_id}/report/html", headers={"X-Valiant-Env": "dev"})
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "run_api_test_report_999" in res.text
    assert "API Test Workflow" in res.text
    assert "Content-Disposition" not in res.headers

    # 2. Fetch download attachment
    res_dl = client.get(f"/api/runs/{run_id}/report/html?download=true", headers={"X-Valiant-Env": "dev"})
    assert res_dl.status_code == 200
    assert "attachment" in res_dl.headers.get("Content-Disposition", "")
    assert f"valiant-report-{run_id}-dev.html" in res_dl.headers.get("Content-Disposition", "")

    # 3. 404 for non-existent run
    res_404 = client.get("/api/runs/nonexistent_run_xyz/report/html", headers={"X-Valiant-Env": "dev"})
    assert res_404.status_code == 404


def test_generate_run_html_report_multitab_features():
    run_data = {
        "id": "run_multitab_comprehensive_123",
        "workflow_name": "Full Multi-Tab Demo",
        "status": "completed",
        "success": True,
        "total_steps": 2,
        "total_time": 10.5,
        "started_at": "2026-10-17T10:00:00",
        "completed_at": "2026-10-17T10:00:10",
        "triggered_by": "qa_lead",
        "inputs": {"db_password": "supersecretpassword", "batch_size": 100},
        "context": {"api_key": "secret-12345", "processed_records": 100},
        "steps": [
            {
                "name": "Step 1: Ingest & Authorize",
                "status": "success",
                "execution_time": 2.5,
                "requires_approval": True,
                "approved_by": "sec_officer",
                "approval_notes": "Security approved for compliance run",
                "approved_at": "2026-10-17T10:00:02",
                "context_delta": {
                    "added": {"ingest_status": "done"},
                    "modified": {"batch_size": 100},
                    "removed": []
                },
                "logs": ["Starting ingestion job...", "Connected to data store.", "Ingestion completed."],
            },
            {
                "name": "Step 2: Polars Analytics",
                "status": "success",
                "execution_time": 8.0,
                "tabular_data": {
                    "total_rows": 2,
                    "total_cols": 2,
                    "columns": [
                        {"name": "metric_name", "type": "str"},
                        {"name": "value", "type": "f64"},
                    ],
                    "preview_rows": [
                        {"metric_name": "accuracy", "value": 0.985},
                        {"metric_name": "latency_ms", "value": 14.2},
                    ]
                }
            }
        ]
    }

    html = generate_run_html_report(run_data, env="uat")

    # 1. Multi-Tab Navigation Verification
    assert 'data-tab="tab-overview"' in html
    assert 'data-tab="tab-steps"' in html
    assert 'data-tab="tab-tabular"' in html
    assert 'data-tab="tab-governance"' in html
    assert 'data-tab="tab-logs"' in html
    assert "switchTab('tab-overview')" in html

    # 2. Executive Overview Tab: Timeline Bar & Masked Inputs
    assert "timeline-bar-segment" in html
    assert "supersecretpassword" not in html
    assert "********" in html
    assert "batch_size" in html

    # 3. Steps Breakdown: Filter pills, Accordions, Context Delta
    assert "filterSteps" in html
    assert "toggleAllSteps" in html
    assert "Context Mutations" in html
    assert "ingest_status" in html

    # 4. Tabular Datasets: Search, Sort, CSV Copy
    assert "filterDataset" in html
    assert "sortTable" in html
    assert "copyTableAsCsv" in html
    assert "accuracy" in html
    assert "latency_ms" in html

    # 5. Governance Audit Trail: Verified Seal & Justification
    assert "VERIFIED GOVERNANCE AUDIT TRAIL" in html
    assert "sec_officer" in html
    assert "Security approved for compliance run" in html

    # 6. Raw Logs & Context: Secret masking & Monospace Terminal
    assert "secret-12345" not in html
    assert "terminal-viewer" in html
    assert "raw-log-content" in html

    # 7. Light / Dark Mode Toggle
    assert "toggleTheme()" in html
    assert "theme-light" in html

