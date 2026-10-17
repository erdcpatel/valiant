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
