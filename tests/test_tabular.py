import os
import shutil
import pytest
import polars as pl
from datetime import datetime
from fastapi.testclient import TestClient

import asyncio
from backend.valiant.core.tabular import (
    is_polars_dataframe,
    to_tabular_payload,
    save_tabular_artifact,
    query_tabular_artifact,
    export_tabular_artifact,
    get_tabular_artifact_path,
)
from backend.valiant.core.runner import WorkflowRunner
from backend.valiant.core.registry import registry
from backend.workflows.sql_query_analytics import SqlQueryAnalyticsWorkflow
from backend.valiant.api.app import app
from backend.valiant.db.database import init_db


@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    test_dir = ".valiant/artifacts/test"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    yield
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)


def test_is_polars_dataframe():
    df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert is_polars_dataframe(df) is True
    assert is_polars_dataframe({"a": [1, 2, 3]}) is False
    assert is_polars_dataframe([1, 2, 3]) is False
    assert is_polars_dataframe(None) is False
    assert is_polars_dataframe("hello") is False


def test_to_tabular_payload():
    df = pl.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "score": [95.5, 82.0, 91.2, 78.4, 88.0],
        "active": [True, False, True, True, False],
        "created_at": [datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 2, 11, 0), datetime(2025, 1, 3, 12, 0), datetime(2025, 1, 4, 13, 0), datetime(2025, 1, 5, 14, 0)]
    })

    payload = to_tabular_payload(df, preview_limit=3)
    assert payload["total_rows"] == 5
    assert payload["total_cols"] == 5
    assert payload["shape"] == [5, 5]
    assert payload["preview_limit"] == 3
    assert len(payload["preview_rows"]) == 3
    assert len(payload["columns"]) == 5

    cols_by_name = {c["name"]: c for c in payload["columns"]}
    assert cols_by_name["id"]["category"] == "numeric"
    assert cols_by_name["name"]["category"] == "string"
    assert cols_by_name["score"]["category"] == "numeric"
    assert cols_by_name["active"]["category"] == "boolean"
    assert cols_by_name["created_at"]["category"] == "datetime"


def test_save_and_query_tabular_artifact():
    df = pl.DataFrame({
        "order_id": list(range(100, 200)),
        "city": ["New York", "London", "Tokyo", "Paris"] * 25,
        "amount": [10.5 * i for i in range(100)],
    })

    run_id = "test-run-101"
    step_name = "fetch_orders"
    env = "test"

    path = save_tabular_artifact(df, run_id, step_name, env)
    assert os.path.exists(path)
    assert path.endswith(".parquet")

    # Test pagination
    query_res = query_tabular_artifact(run_id, step_name, env=env, page=1, page_size=20)
    assert query_res["total_rows"] == 100
    assert query_res["page"] == 1
    assert query_res["page_size"] == 20
    assert query_res["total_pages"] == 5
    assert len(query_res["rows"]) == 20
    assert query_res["has_artifact"] is True

    # Test search filter
    search_res = query_tabular_artifact(run_id, step_name, env=env, search="Tokyo", page=1, page_size=50)
    assert search_res["total_rows"] == 25
    assert len(search_res["rows"]) == 25
    assert all(r["city"] == "Tokyo" for r in search_res["rows"])

    # Test sorting
    sorted_res = query_tabular_artifact(run_id, step_name, env=env, sort_by="amount", sort_desc=True, page=1, page_size=5)
    first_amount = sorted_res["rows"][0]["amount"]
    second_amount = sorted_res["rows"][1]["amount"]
    assert first_amount > second_amount


def test_export_tabular_artifact():
    df = pl.DataFrame({
        "customer": ["Alice", "Bob", "Charlie"],
        "spend": [120.50, 450.00, 89.20]
    })
    run_id = "test-export-run"
    step_name = "customer_spend"
    env = "test"
    save_tabular_artifact(df, run_id, step_name, env)

    # CSV export
    content, media_type, filename = export_tabular_artifact(run_id, step_name, env, "csv")
    assert b"Alice,120.5" in content
    assert filename.endswith(".csv")
    assert media_type == "text/csv"

    # Parquet export
    p_content, p_media, p_filename = export_tabular_artifact(run_id, step_name, env, "parquet")
    assert len(p_content) > 0
    assert p_filename.endswith(".parquet")

    # JSON export
    j_content, j_media, j_filename = export_tabular_artifact(run_id, step_name, env, "json")
    assert b"Alice" in j_content
    assert j_filename.endswith(".json")


def test_workflow_runner_auto_captures_polars():
    async def _async_test():
        init_db("test")
        wf = SqlQueryAnalyticsWorkflow()
        runner = WorkflowRunner(workflow=wf, environment="test")
        res = await runner.run(inputs={"row_count": 100, "min_order_amount": 50.0})

        assert res.status == "completed"
        assert len(res.results) == 4

        step1 = next(s for s in res.results if s.name == "Fetch SQL Sales Data")
        assert step1.success is True
        assert step1.tabular_data is not None
        assert step1.tabular_data["total_rows"] == 100
        assert step1.tabular_data["has_artifact"] is True
        assert len(step1.tabular_data["preview_rows"]) <= 50

        # Step 2 SQL aggregation
        step2 = next(s for s in res.results if s.name == "Aggregate Regional Revenue")
        assert step2.success is True
        assert step2.tabular_data is not None
        assert step2.tabular_data["total_rows"] > 0

        # Step 3 Outlier detection
        step3 = next(s for s in res.results if s.name == "Detect Outlier Transactions")
        assert step3.success is True
        assert step3.tabular_data is not None

        # Verify Parquet artifact exists on disk
        artifact_path = get_tabular_artifact_path("test", res.run_id, "Fetch SQL Sales Data")
        assert os.path.exists(artifact_path)

        # Test API endpoints with TestClient
        client = TestClient(app)
        api_res = client.get(
            f"/api/runs/{res.run_id}/steps/Fetch SQL Sales Data/tabular/data",
            params={"page": 1, "page_size": 15},
            headers={"X-Valiant-Env": "test"}
        )
        assert api_res.status_code == 200
        payload = api_res.json()
        assert payload["total_rows"] == 100
        assert len(payload["rows"]) == 15

        # Test Export endpoint
        export_res = client.get(
            f"/api/runs/{res.run_id}/steps/Fetch SQL Sales Data/tabular/export",
            params={"format": "csv"},
            headers={"X-Valiant-Env": "test"}
        )
        assert export_res.status_code == 200
        assert "order_id" in export_res.text

    asyncio.run(_async_test())
