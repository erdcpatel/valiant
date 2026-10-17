"""
Compact Micro-Workflow Showcase
Demonstrating zero-ceremony functional workflow authoring, direct parameter injection,
auto-ordering, approval gates, and Polars tabular auto-wrapping.
"""
from typing import Literal
import polars as pl
from backend.valiant import workflow

# Define workflow in a single line
wf = workflow(
    "compact_micro_workflow",
    description="Showcase of ultra-compact functional workflow with parameter injection and Polars",
    tags=["compact", "functional", "showcase"]
)

# 1. Inputs can be declared explicitly or inferred from step parameters
wf.input("batch_id", type=str, default="BATCH-2026-X", help_text="Batch identifier")
wf.input("record_count", type=int, default=25, help_text="Number of records to simulate")
wf.input("mode", type=str, options=["fast", "standard", "deep"], default="fast")


@wf.step("Validate Batch Parameters")
def validate(batch_id: str, record_count: int, mode: str):
    # Notice: parameters are automatically injected from context/inputs!
    # No `self.success(...)` ceremony required - strings auto-wrap into StepResult!
    return f"Validated batch {batch_id} with {record_count} records in {mode} mode"


@wf.step("Generate Tabular Data")
async def generate_records(ctx, record_count: int = 25):
    # Log progress in real-time
    ctx.log(f"Simulating generation of {record_count} telemetry records")

    # Polars DataFrames are automatically captured and wrapped into tabular artifacts!
    df = pl.DataFrame({
        "record_id": [f"REC-{1000 + i}" for i in range(record_count)],
        "sensor_reading": [round(20.0 + (i * 0.75), 2) for i in range(record_count)],
        "status": ["healthy" if i % 5 != 0 else "warning" for i in range(record_count)],
        "active": [True for _ in range(record_count)],
    })

    # Return Polars DataFrame directly - runner auto-wraps and creates Parquet artifact!
    return df


@wf.approval("Operator Review", prompt="Review generated tabular telemetry before final settlement?")
def operator_review():
    pass


@wf.step("Finalize Batch Settlement")
def finalize(batch_id: str, ctx):
    ctx["settled"] = True
    return {"batch_id": batch_id, "settled": True, "message": "Batch settlement complete"}
