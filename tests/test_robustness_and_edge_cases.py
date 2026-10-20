"""
Comprehensive robustness and edge-case regression test suite.
Verifies platform resilience across runner, typing, secret masking, tabular data, and reporting.
"""
import os
import math
import json
import tempfile
import pytest
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path

from backend.valiant.core.context import WorkflowContext
from backend.valiant.core.workflow import Workflow, step, workflow
from backend.valiant.core.runner import WorkflowRunner
from backend.valiant.core.registry import WorkflowRegistry
from backend.valiant.core.tabular import (
    to_tabular_payload,
    save_tabular_artifact,
    query_tabular_artifact,
    is_polars_dataframe
)
from backend.valiant.core.report import generate_run_html_report


def test_secret_masking_with_falsy_values():
    """Verify context.to_dict(mask_secrets=True) masks secrets even when value is falsy (0, False)."""
    ctx = WorkflowContext()
    ctx.set("secret_pin", 0)
    ctx.set("auth_flag", False)
    ctx.set("normal_zero", 0)
    ctx.mark_sensitive("secret_pin")
    ctx.mark_sensitive("auth_flag")

    dumped = ctx.to_dict(mask_secrets=True)
    assert dumped["secret_pin"] == "********", "Falsy integer secret was not masked!"
    assert dumped["auth_flag"] == "********", "Falsy boolean secret was not masked!"
    assert dumped["normal_zero"] == 0, "Non-sensitive zero was incorrectly masked!"


def test_auto_type_coercion_in_runner():
    """Verify runner auto-coerces CLI/string inputs into annotated int, float, bool types."""
    import asyncio

    @workflow("type_coercion_test", description="Test auto coercion")
    class TypeCoercionWorkflow(Workflow):
        @step("Check Types")
        def check_types(self, count: int, ratio: float, active: bool, name: str):
            assert isinstance(count, int), f"count should be int, got {type(count)}"
            assert count == 42
            assert isinstance(ratio, float), f"ratio should be float, got {type(ratio)}"
            assert ratio == 3.14
            assert isinstance(active, bool), f"active should be bool, got {type(active)}"
            assert active is True
            assert isinstance(name, str)
            return {"coerced": True, "count": count, "ratio": ratio, "active": active}

    wf = TypeCoercionWorkflow()
    runner = WorkflowRunner(workflow=wf, environment="dev")
    
    # Pass all values as strings (mimicking CLI --set count=42 --set ratio=3.14 --set active=true)
    string_inputs = {
        "count": "42",
        "ratio": "3.14",
        "active": "true",
        "name": "Valiant"
    }
    result = asyncio.run(runner.run(string_inputs))
    assert result.success is True, f"Workflow failed: {result.results[0].message if result.results else 'No results'}"
    assert result.results[0].data["coerced"] is True


def test_empty_and_whitespace_command_exec_graceful():
    """Verify context.exec on empty strings or whitespace returns failed result without crashing."""
    import asyncio

    async def _test():
        ctx = WorkflowContext()
        res_empty = await ctx.exec("")
        assert not res_empty.success
        assert res_empty.exit_code == -1
        assert "empty" in res_empty.stderr.lower()

        res_space = await ctx.exec("     ")
        assert not res_space.success
        assert res_space.exit_code == -1

        res_list = await ctx.exec([])
        assert not res_list.success
        assert res_list.exit_code == -1

    asyncio.run(_test())


def test_tabular_engine_handles_nan_and_complex_types():
    """Verify Polars DataFrame with NaN, Decimal, bytes, and Dates exports to clean JSON."""
    import polars as pl

    df = pl.DataFrame({
        "item_id": [1, 2],
        "score": [float("nan"), 99.9],
        "cost": [Decimal("19.99"), Decimal("49.50")],
        "raw": [b"payload_1", b"payload_2"],
        "created_at": [datetime(2026, 1, 15, 10, 30), datetime(2026, 2, 20, 14, 0)]
    })

    payload = to_tabular_payload(df, dataset_name="complex_records")
    assert payload["total_rows"] == 2
    assert payload["total_columns"] == 5

    # Verify JSON serialization succeeds without Nan or type errors
    json_str = json.dumps(payload)
    parsed = json.loads(json_str)
    assert parsed["preview_rows"][0]["score"] is None
    assert parsed["preview_rows"][0]["cost"] == 19.99
    assert parsed["preview_rows"][0]["raw"] == "payload_1"


def test_tabular_pagination_clamping():
    """Verify query_tabular_artifact handles out-of-range pagination parameters safely."""
    import polars as pl

    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["VALIANT_ARTIFACT_DIR"] = tmp_dir
        df = pl.DataFrame({"idx": list(range(10)), "val": [f"val_{i}" for i in range(10)]})
        save_tabular_artifact(df, run_id="run_clamp_test", step_name="step_table", env="dev")

        # Clamp page_size=0 -> should clamp to 1
        res_zero = query_tabular_artifact(
            run_id="run_clamp_test",
            step_name="step_table",
            env="dev",
            page=0,
            page_size=0
        )
        assert res_zero["success"] is True
        assert res_zero["page"] == 1
        assert res_zero["page_size"] == 1

        # Clamp huge page_size -> should clamp to 1000
        res_huge = query_tabular_artifact(
            run_id="run_clamp_test",
            step_name="step_table",
            env="dev",
            page=1,
            page_size=50000
        )
        assert res_huge["success"] is True
        assert res_huge["page_size"] == 1000


def test_registry_get_instance_universal():
    """Verify registry.get_instance works seamlessly for both class and functional workflows."""
    reg = WorkflowRegistry()

    # Class-based workflow
    class SampleClassWorkflow(Workflow):
        workflow_id = "sample_class"
        name = "Sample Class"

    reg.register("sample_class", SampleClassWorkflow)

    # Functional workflow
    sample_func = workflow("sample_func", description="Functional test")

    reg.register("sample_func", sample_func)

    inst1 = reg.get_instance("sample_class")
    inst2 = reg.get_instance("sample_func")

    assert isinstance(inst1, Workflow)
    assert isinstance(inst2, Workflow)
    assert inst1.name == "Sample Class"
    assert inst2.workflow_id == "sample_func"


def test_html_report_handles_edge_cases():
    """Verify generate_run_html_report handles 0 duration, empty steps, and None contexts without error."""
    minimal_run_data = {
        "id": "run_test_edge",
        "workflow_name": "Edge Workflow",
        "status": "completed",
        "total_time": 0.0,
        "started_at": "2026-10-17T22:00:00Z",
        "completed_at": "2026-10-17T22:00:00Z",
        "steps": [],
        "context": None,
        "inputs": None
    }

    html_out = generate_run_html_report(minimal_run_data, env="dev")
    assert "<!DOCTYPE html>" in html_out
    assert "Edge Workflow" in html_out
    assert "ValiantFlow Platform" in html_out


def test_api_health_returns_dynamic_version():
    """Verify /api/health returns the actual package __version__, not hardcoded 3.0.0."""
    from fastapi.testclient import TestClient
    from backend.valiant.api.app import app
    from backend.valiant import __version__

    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == __version__


def test_comparator_handles_none_runs_gracefully():
    """Verify compare_runs_data handles None or empty runs without raising AttributeError."""
    from backend.valiant.core.comparator import compare_runs_data

    res_none = compare_runs_data(None, None)
    assert "error" in res_none["summary"]

    res_empty = compare_runs_data({}, {"id": "run_1"})
    assert "error" in res_empty["summary"]


def test_sqlite_wal_mode_and_concurrency_settings():
    """Verify SQLite database engine initializes with WAL mode and connect timeout."""
    from sqlalchemy import text
    from backend.valiant.db.database import get_engine

    eng = get_engine("dev")
    with eng.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode;")).scalar()
        assert str(journal_mode).lower() == "wal", f"Expected WAL mode, got {journal_mode}"

