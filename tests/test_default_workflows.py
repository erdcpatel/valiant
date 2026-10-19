import os
import pytest
from fastapi.testclient import TestClient

from backend.valiant.core.registry import WorkflowRegistry
from backend.valiant.api.app import app


client = TestClient(app)


def test_registry_marks_default_workflows():
    registry = WorkflowRegistry()
    registry.discover()
    all_wfs = registry.list_workflows(include_defaults=True)
    assert len(all_wfs) > 0

    # Workflows from backend/workflows/ are marked as is_default = True
    default_wfs = [w for w in all_wfs.values() if w.get("is_default") is True]
    assert len(default_wfs) > 0

    # Filtering with include_defaults=False omits them
    custom_only = registry.list_workflows(include_defaults=False)
    for wf in custom_only.values():
        assert wf.get("is_default") is not True


def test_api_workflows_include_defaults_param():
    # When include_defaults is true (default)
    res_all = client.get("/api/workflows?include_defaults=true")
    assert res_all.status_code == 200
    data_all = res_all.json().get("data", {})
    assert len(data_all) > 0
    assert any(wf.get("is_default") is True for wf in data_all.values())

    # When include_defaults is false
    res_custom = client.get("/api/workflows?include_defaults=false")
    assert res_custom.status_code == 200
    data_custom = res_custom.json().get("data", {})
    for wf_id, wf_meta in data_custom.items():
        assert wf_meta.get("is_default") is not True


def test_api_workflows_env_var_override(monkeypatch):
    monkeypatch.setenv("VALIANT_HIDE_DEFAULTS", "1")
    res = client.get("/api/workflows")
    assert res.status_code == 200
    data = res.json().get("data", {})
    for wf_id, wf_meta in data.items():
        assert wf_meta.get("is_default") is not True


def test_custom_project_workflows_in_various_structures(monkeypatch):
    """Verify workflows in standard project structures are discovered and never marked as default."""
    import tempfile
    from pathlib import Path
    from typer.testing import CliRunner
    from backend.valiant.cli.main import app

    runner = CliRunner()

    with tempfile.TemporaryDirectory() as td:
        project_dir = Path(td)

        # Structure 1: workflows/
        wf1 = project_dir / "workflows" / "order_pipeline.py"
        wf1.parent.mkdir(parents=True)
        wf1.write_text("""
from backend.valiant import Workflow, step

class OrderPipelineWorkflow(Workflow):
    name = "Order Pipeline"
    @step("Process")
    def process(self):
        return self.success()
""", encoding="utf-8")

        # Structure 2: Nested subdirectory in workflows/
        wf2 = project_dir / "workflows" / "nested" / "deep_sync.py"
        wf2.parent.mkdir(parents=True)
        wf2.write_text("""
from backend.valiant import Workflow, step

class DeepSyncWorkflow(Workflow):
    name = "Deep Sync"
    @step("Sync")
    def sync_data(self):
        return self.success()
""", encoding="utf-8")

        # Structure 3: src/workflows/
        wf3 = project_dir / "src" / "workflows" / "analytics_flow.py"
        wf3.parent.mkdir(parents=True)
        wf3.write_text("""
from backend.valiant import Workflow, step

class AnalyticsFlow(Workflow):
    @step("Analyze")
    def analyze(self):
        return self.success()
""", encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            reg = WorkflowRegistry()
            reg.discover()

            all_wfs = reg.list_workflows(include_defaults=True)
            custom_wfs = reg.list_workflows(include_defaults=False)

            # All 3 custom workflows must be discovered
            assert "order_pipeline" in all_wfs
            assert "deep_sync" in all_wfs
            assert "analytics_flow" in all_wfs

            # None of them should be marked as default
            assert all_wfs["order_pipeline"]["is_default"] is False
            assert all_wfs["deep_sync"]["is_default"] is False
            assert all_wfs["analytics_flow"]["is_default"] is False

            # Custom-only listing must contain all 3 and no templates
            assert "order_pipeline" in custom_wfs
            assert "deep_sync" in custom_wfs
            assert "analytics_flow" in custom_wfs
            assert "demo" not in custom_wfs
            assert "bom_test_automation" not in custom_wfs

            # CLI testing in user project: valiant list --no-defaults
            res_nodef = runner.invoke(app, ["list", "--no-defaults"])
            assert res_nodef.exit_code == 0
            assert "Custom Project Workflows" in res_nodef.output
            assert "order_pipeline" in res_nodef.output
            assert "deep_sync" in res_nodef.output
            assert "analytics_flow" in res_nodef.output
            assert "Built-in Template Workflows" not in res_nodef.output

            # CLI testing with defaults: both tables present
            res_all = runner.invoke(app, ["list", "--defaults"])
            assert res_all.exit_code == 0
            assert "Custom Project Workflows" in res_all.output
            assert "Built-in Template Workflows" in res_all.output

        finally:
            os.chdir(old_cwd)


def test_subclass_id_derivation_without_collision():
    """Verify subclasses without explicit workflow_id auto-derive unique IDs instead of colliding on 'workflow'."""
    from backend.valiant import Workflow, step
    from backend.valiant.core.registry import _derive_workflow_id

    class OrderFulfillmentWorkflow(Workflow):
        pass

    class CustomerBillingWorkflow(Workflow):
        pass

    class LegacyCustom(Workflow):
        name = "My Custom Sync Job"

    id1 = _derive_workflow_id(OrderFulfillmentWorkflow, "order_fulfillment")
    id2 = _derive_workflow_id(CustomerBillingWorkflow, "customer_billing")
    id3 = _derive_workflow_id(LegacyCustom, "legacy")

    assert id1 == "order_fulfillment"
    assert id2 == "customer_billing"
    assert id3 == "my_custom_sync_job"
    assert id1 != id2
    assert id1 != "workflow"

