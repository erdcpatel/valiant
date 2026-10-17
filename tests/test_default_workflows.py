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
