"""
Unit and integration tests for Compact Workflows, Type-Annotated Inputs,
Direct Parameter Injection, Auto-Ordering, and Functional Micro-Workflows.
"""
import pytest
from typing import Literal, Optional
import polars as pl

from backend.valiant import (
    Workflow,
    FunctionalWorkflow,
    step,
    workflow,
    WorkflowRunner,
    StepStatus,
    WorkflowStatus,
    InputType,
    registry,
)


class SampleCompactClassWorkflow(Workflow):
    name = "Sample Compact Class"
    # Type-annotated class attributes (Pydantic / Dataclass style)
    user_name: str = "Alice"
    max_items: int = 50
    dry_run: bool = False
    tier: Literal["free", "pro", "enterprise"] = "pro"
    api_token: str = "super-secret-token"

    @step("Step One")
    def step_one(self, user_name: str, max_items: int):
        return f"Hello {user_name}, max={max_items}"

    @step("Step Two")
    def step_two(self, ctx, dry_run: bool):
        ctx["executed_two"] = True
        return {"dry_run": dry_run, "status": "completed"}


def test_type_annotated_workflow_inputs():
    """Verify that type-annotated class attributes auto-generate InputFields."""
    wf = SampleCompactClassWorkflow()
    inputs = wf.inputs()

    assert len(inputs) == 5
    input_map = {f.name: f for f in inputs}

    assert "user_name" in input_map
    assert input_map["user_name"].type == InputType.TEXT
    assert input_map["user_name"].default == "Alice"

    assert "max_items" in input_map
    assert input_map["max_items"].type == InputType.NUMBER
    assert input_map["max_items"].default == 50

    assert "dry_run" in input_map
    assert input_map["dry_run"].type == InputType.CHECKBOX
    assert input_map["dry_run"].default is False

    assert "tier" in input_map
    assert input_map["tier"].type == InputType.SELECT
    assert input_map["tier"].options == ["free", "pro", "enterprise"]
    assert input_map["tier"].default == "pro"

    assert "api_token" in input_map
    assert input_map["api_token"].type == InputType.PASSWORD
    assert input_map["api_token"].sensitive is True


def test_auto_step_ordering():
    """Verify steps without explicit 'order' are auto-sequenced in declaration order."""
    class OrderingTestWorkflow(Workflow):
        @step("First")
        def first(self):
            return "First"

        @step("Second")
        def second(self):
            return "Second"

        @step("Third")
        def third(self):
            return "Third"

    wf = OrderingTestWorkflow()
    steps = wf.get_steps()

    assert len(steps) == 3
    names = [cfg.name for cfg, _ in steps]
    orders = [cfg.order for cfg, _ in steps]

    assert names == ["First", "Second", "Third"]
    assert orders[0] < orders[1] < orders[2]


@pytest.mark.anyio
async def test_auto_result_wrapping_and_parameter_injection():
    """Verify automatic wrapping of Polars DataFrames, booleans, strings, dicts, and parameter injection."""
    class ResultsWorkflow(Workflow):
        @step("String Step")
        def string_step(self, user_name: str = "World"):
            return f"Hello {user_name}"

        @step("Bool Success")
        def bool_success(self):
            return True

        @step("Dict Step")
        def dict_step(self):
            return {"key": "value", "processed": 42}

        @step("Polars Step")
        def polars_step(self):
            return pl.DataFrame({
                "col1": [1, 2, 3],
                "col2": ["a", "b", "c"]
            })

    wf = ResultsWorkflow()
    runner = WorkflowRunner(workflow=wf, environment="dev")
    res = await runner.run({"user_name": "Antigravity"})

    assert res.success is True
    assert res.status == WorkflowStatus.COMPLETED

    step_results = runner.step_results
    assert len(step_results) == 4

    # 1. String auto-wrapping
    assert step_results[0].name == "String Step"
    assert step_results[0].success is True
    assert step_results[0].message == "Hello Antigravity"

    # 2. Bool auto-wrapping
    assert step_results[1].name == "Bool Success"
    assert step_results[1].success is True

    # 3. Dict auto-wrapping
    assert step_results[2].name == "Dict Step"
    assert step_results[2].success is True
    assert step_results[2].data["processed"] == 42

    # 4. Polars DataFrame auto-wrapping
    assert step_results[3].name == "Polars Step"
    assert step_results[3].success is True
    assert step_results[3].tabular_data is not None
    assert step_results[3].tabular_data["total_rows"] == 3
    assert [c["name"] for c in step_results[3].tabular_data["columns"]] == ["col1", "col2"]


@pytest.mark.anyio
async def test_functional_workflow_e2e():
    """Verify functional micro-workflow authoring with fluent steps and parameter injection."""
    fw = FunctionalWorkflow(
        name="test_micro_wf",
        description="Functional test workflow",
        tags=["micro", "test"]
    )
    fw.input("task_name", type=str, default="TaskA")
    fw.input("count", type=int, default=10)

    @fw.step("Prepare")
    def prepare(task_name: str, count: int):
        return f"Prepared {task_name} with count {count}"

    @fw.step("Execute")
    async def execute(ctx, count: int):
        ctx.log(f"Executing count={count}")
        ctx["executed"] = True
        return {"count": count, "done": True}

    steps = fw.get_steps()
    assert len(steps) == 2
    assert steps[0][0].name == "Prepare"
    assert steps[1][0].name == "Execute"

    runner = WorkflowRunner(workflow=fw, environment="dev")
    res = await runner.run({"task_name": "ComputeHash", "count": 100})

    assert res.success is True
    assert res.status == WorkflowStatus.COMPLETED
    assert runner.step_results[0].message == "Prepared ComputeHash with count 100"
    assert runner.step_results[1].data["done"] is True


def test_registry_discovery_of_compact_showcase():
    """Verify that WorkflowRegistry discovers the new compact micro-workflow showcase."""
    registry.discover()
    wf_obj = registry.get("compact_micro_workflow")
    assert wf_obj is not None

    instance = wf_obj() if isinstance(wf_obj, type) else wf_obj
    steps = instance.get_steps()
    assert len(steps) == 4
    step_names = [s[0].name for s in steps]
    assert "Validate Batch Parameters" in step_names
    assert "Generate Tabular Data" in step_names
    assert "Operator Review" in step_names
    assert "Finalize Batch Settlement" in step_names

    inputs = instance.inputs()
    input_names = [f.name for f in inputs]
    assert "batch_id" in input_names
    assert "record_count" in input_names
    assert "mode" in input_names
