"""
Tests for CLI commands (init, list, run, runs) and workflow discovery isolation.
"""
import os
import sys
import tempfile
import pytest
from pathlib import Path
from typer.testing import CliRunner
from backend.valiant.cli.main import app
from backend.valiant.core.registry import WorkflowRegistry

runner = CliRunner()


def test_registry_does_not_execute_root_directory_scripts():
    """Verify registry.discover() does NOT scan and execute *.py in Path.cwd()."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create a trap script in the root directory that writes a marker file if executed
        trap_script = tmp_path / "root_script.py"
        marker_file = tmp_path / "trap_executed.marker"
        trap_script.write_text(f"""
from pathlib import Path
Path({repr(str(marker_file))}).write_text('TRAP_EXECUTED')
""", encoding="utf-8")

        # Create a legitimate workflow in workflows/
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        (wf_dir / "my_flow.py").write_text("""
from valiantflow import workflow

wf = workflow("isolated_test_wf", description="Test flow")

@wf.step("Step 1")
def step_1():
    return "ok"
""", encoding="utf-8")

        # Change cwd to tmp_path and run discovery
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_dir)
            test_reg = WorkflowRegistry()
            test_reg.discover()

            # Marker file must NOT have been created by root_script.py
            assert not marker_file.exists(), "Root directory script was improperly executed during auto-discovery!"
            # Workflow in workflows/ must be discovered
            assert "isolated_test_wf" in test_reg.list_workflows()
        finally:
            os.chdir(old_cwd)


def test_registry_discover_single_file():
    """Verify registry.discover() can discover a workflow from a single .py file path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        wf_file = Path(tmp_dir) / "custom_flow.py"
        wf_file.write_text("""
from valiantflow import workflow

wf = workflow("single_file_wf", description="Single file flow")

@wf.step("Step 1")
def step_1():
    return "done"
""", encoding="utf-8")

        test_reg = WorkflowRegistry()
        test_reg.discover(search_dirs=[str(wf_file)])
        assert "single_file_wf" in test_reg.list_workflows()


def test_cli_init_command():
    """Verify 'valiant init' bootstraps a project structure with starter template and .env."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = runner.invoke(app, ["init", "--dir", tmp_dir, "--style", "compact"])
        assert result.exit_code == 0
        assert "ValiantFlow project initialized successfully" in result.output

        workflows_dir = Path(tmp_dir) / "workflows"
        starter_file = workflows_dir / "starter_workflow.py"
        env_file = Path(tmp_dir) / ".env"

        assert workflows_dir.is_dir()
        assert starter_file.is_file()
        assert env_file.is_file()

        # Check content
        assert "class StarterWorkflow" in starter_file.read_text(encoding="utf-8")
        assert "VALIANT_ENV=dev" in env_file.read_text(encoding="utf-8")


def test_cli_runs_accepts_env_flag():
    """Verify 'valiant runs' accepts --env flag without throwing error."""
    result = runner.invoke(app, ["runs", "--env", "uat"])
    assert result.exit_code == 0
    # Should display UAT table or no history message
    assert "UAT" in result.output


def test_cli_list_with_dir():
    """Verify 'valiant list --dir' discovers workflows in the specified directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        wf_file = Path(tmp_dir) / "special_flow.py"
        wf_file.write_text("""
from valiantflow import workflow

wf = workflow("special_flow", description="Special flow")

@wf.step("Step 1")
def step_1():
    return "done"
""", encoding="utf-8")

        result = runner.invoke(app, ["list", "--dir", tmp_dir, "--no-defaults"])
        assert result.exit_code == 0
        assert "special_flow" in result.output


def test_context_exec_empty_command_graceful():
    """Verify context.exec('') returns failed CommandResult rather than crashing."""
    import asyncio
    from backend.valiant.core.context import WorkflowContext

    async def _run():
        ctx = WorkflowContext()
        res = await ctx.exec("")
        assert not res.success
        assert res.exit_code == -1
        assert "Command list cannot be empty" in res.stderr

    asyncio.run(_run())


def test_tabular_data_json_safety_with_nan_decimal_bytes():
    """Verify Polars DataFrame with NaNs, Decimals, bytes, and dates serializes safely."""
    import polars as pl
    from decimal import Decimal
    from datetime import date
    import json
    from backend.valiant.core.tabular import to_tabular_payload

    df = pl.DataFrame({
        "name": ["Alice", "Bob"],
        "score": [95.5, float("nan")],
        "amount": [Decimal("100.25"), Decimal("250.50")],
        "raw_bytes": [b"hello", b"world"],
        "joined": [date(2026, 1, 1), date(2026, 6, 1)]
    })

    payload = to_tabular_payload(df, dataset_name="edge_case_data")
    assert payload["total_rows"] == 2
    
    # Must be 100% standard JSON-serializable
    dumped = json.dumps(payload)
    parsed = json.loads(dumped)
    assert parsed["dataset_name"] == "edge_case_data"
    assert parsed["preview_rows"][1]["score"] is None  # NaN converted to None


def test_tabular_pagination_clamp_zero_division():
    """Verify query_tabular_artifact handles page_size=0 without ZeroDivisionError."""
    import polars as pl
    import tempfile
    from backend.valiant.core.tabular import save_tabular_artifact, query_tabular_artifact

    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["VALIANT_ARTIFACT_DIR"] = tmp_dir
        df = pl.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
        save_tabular_artifact(df, run_id="run_clamp_test", step_name="step_table", env="dev")

        # Passing page_size=0 should be safely clamped to page_size=1
        res = query_tabular_artifact(
            run_id="run_clamp_test",
            step_name="step_table",
            env="dev",
            page=0,
            page_size=0
        )
        assert res["success"] is True
        assert res["page"] == 1
        assert res["page_size"] == 1


def test_cli_new_sanitizes_identifier():
    """Verify 'valiant new' sanitizes kebab-case to snake_case Python identifiers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = runner.invoke(app, ["new", "my-kebab-pipeline", "--dir", tmp_dir])
        assert result.exit_code == 0
        assert "my-kebab-pipeline" in result.output
        assert "my_kebab_pipeline" in result.output
        target_file = Path(tmp_dir) / "my_kebab_pipeline.py"
        assert target_file.is_file()
        assert "class MyKebabPipelineWorkflow" in target_file.read_text(encoding="utf-8")


def test_cli_run_warns_on_malformed_set():
    """Verify 'valiant run' warns on malformed key-value parameters."""
    result = runner.invoke(app, ["run", "demo", "--set", "malformed_no_equals"])
    # Should warn about malformed argument
    assert "Warning: Ignoring malformed --set argument" in result.output

