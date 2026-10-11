"""
Unit and integration tests for Valiant Run Comparator (P4).
"""
import pytest
from backend.valiant.core.comparator import compare_runs_data
from backend.valiant.api.app import app
from fastapi.testclient import TestClient


def test_compare_runs_identical_runs():
    run_a = {
        "id": "run_001",
        "workflow_name": "data_pipeline",
        "status": "completed",
        "success": True,
        "total_time": 1.25,
        "environment": "dev",
        "inputs": {"count": 10},
        "context": {"processed": 10},
        "steps": [
            {
                "name": "Step 1",
                "status": "success",
                "success": True,
                "time_taken": 0.5,
                "error": None,
                "message": "OK",
            },
            {
                "name": "Step 2",
                "status": "success",
                "success": True,
                "time_taken": 0.75,
                "error": None,
                "message": "Done",
            },
        ],
    }
    run_b = {
        "id": "run_002",
        "workflow_name": "data_pipeline",
        "status": "completed",
        "success": True,
        "total_time": 1.25,
        "environment": "dev",
        "inputs": {"count": 10},
        "context": {"processed": 10},
        "steps": [
            {
                "name": "Step 1",
                "status": "success",
                "success": True,
                "time_taken": 0.5,
                "error": None,
                "message": "OK",
            },
            {
                "name": "Step 2",
                "status": "success",
                "success": True,
                "time_taken": 0.75,
                "error": None,
                "message": "Done",
            },
        ],
    }

    result = compare_runs_data(run_a, run_b)
    summary = result["summary"]

    assert summary["outcome"] == "same"
    assert summary["time_delta"] == 0.0
    assert summary["time_ratio"] == 1.0
    assert summary["regressed_steps_count"] == 0
    assert summary["inputs_differ_count"] == 0
    assert summary["context_differ_count"] == 0
    assert len(result["step_comparisons"]) == 2
    for sc in result["step_comparisons"]:
        assert sc["match_type"] == "matched"


def test_compare_runs_detects_regression_and_diffs():
    run_baseline = {
        "id": "run_base",
        "workflow_name": "data_pipeline",
        "status": "completed",
        "success": True,
        "total_time": 1.0,
        "environment": "dev",
        "inputs": {"batch_size": 50},
        "context": {"records": 50},
        "steps": [
            {
                "name": "Extract",
                "status": "success",
                "success": True,
                "time_taken": 0.4,
                "error": None,
            },
            {
                "name": "Transform",
                "status": "success",
                "success": True,
                "time_taken": 0.6,
                "error": None,
            },
        ],
    }
    run_target = {
        "id": "run_target",
        "workflow_name": "data_pipeline",
        "status": "failed",
        "success": False,
        "total_time": 1.8,
        "environment": "prod",
        "inputs": {"batch_size": 100},
        "context": {"records": 0, "error_code": "ERR_OOM"},
        "steps": [
            {
                "name": "Extract",
                "status": "success",
                "success": True,
                "time_taken": 0.9,
                "error": None,
            },
            {
                "name": "Transform",
                "status": "failed",
                "success": False,
                "time_taken": 0.9,
                "error": "Out of memory",
            },
        ],
    }

    result = compare_runs_data(run_baseline, run_target)
    summary = result["summary"]

    assert summary["outcome"] == "regression"
    assert summary["regressed_steps_count"] == 1
    assert summary["time_delta"] == 0.8
    assert summary["time_ratio"] == 1.8

    # Inputs diff verification
    assert "batch_size" in result["inputs_diff"]
    assert result["inputs_diff"]["batch_size"] == {"a": 50, "b": 100}

    # Context diff verification
    assert "records" in result["context_diff"]
    assert result["context_diff"]["records"] == {"a": 50, "b": 0}
    assert "error_code" in result["context_diff"]

    # Step matrix verification
    transform_step = next(s for s in result["step_comparisons"] if s["name"] == "Transform")
    assert transform_step["match_type"] == "regressed"
    assert transform_step["error_b"] == "Out of memory"


def test_comparator_api_endpoint():
    client = TestClient(app)

    # Missing required query params should return 422 Unprocessable Entity
    res = client.get("/api/runs/compare/diff")
    assert res.status_code == 422

    # Non-existent run should return 404
    res = client.get("/api/runs/compare/diff?run_a=nonexistent1&run_b=nonexistent2&env_a=dev&env_b=dev")
    assert res.status_code == 404
