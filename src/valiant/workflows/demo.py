"""
Demo workflow — showcases every feature of the Valiant v3 engine.

Run it:
    valiant run demo --set name="Alice" --set count=3

Via API:
    POST /runs/demo  {"inputs": {"name": "Alice", "count": 3}}
"""
from __future__ import annotations

import random
import time

from valiant.core.context import WorkflowContext
from valiant.core.models import InputField, InputType, StepResult
from valiant.core.workflow import Workflow, step, workflow


@workflow(
    name="demo",
    description="End-to-end demo — shows sequential steps, parallel execution, retries, and metrics.",
    tags=["demo", "example"],
    version="3.0.0",
)
class DemoWorkflow(Workflow):

    def get_input_fields(self) -> list[InputField]:
        return [
            InputField(
                name="name",
                label="Your Name",
                type=InputType.TEXT,
                required=True,
                description="Name to greet",
            ),
            InputField(
                name="count",
                label="Item Count",
                type=InputType.NUMBER,
                required=False,
                default=5,
                min_value=1,
                max_value=100,
                description="Number of items to process",
            ),
            InputField(
                name="environment",
                label="Environment",
                type=InputType.SELECT,
                required=False,
                default="development",
                options=["development", "staging", "production"],
            ),
            InputField(
                name="notify",
                label="Send Notification",
                type=InputType.BOOLEAN,
                required=False,
                default=False,
            ),
        ]

    # ── Steps ──────────────────────────────────────────────────────────────────

    @step(name="Validate Input", order=1, description="Validates all workflow inputs")
    def validate_input(self, ctx: WorkflowContext) -> StepResult:
        name = ctx["name"]
        count = int(ctx.get("count", 5))
        env = ctx.get("environment", "development")

        if len(name.strip()) < 2:
            return self.failure("Name must be at least 2 characters.", tags=["validation-error"])

        return self.success(
            f"Inputs valid — greeting {name!r} in {env}",
            data={"validated_name": name.strip(), "count": count, "env": env},
            metrics={"input_length": float(len(name))},
            tags=["validated"],
        )

    @step(name="Fetch Data", order=2, requires=["Validate Input"],
          description="Simulates fetching data from an external source", retries=2)
    def fetch_data(self, ctx: WorkflowContext) -> StepResult:
        count = ctx.get_data("Validate Input", "count") or 5
        time.sleep(0.2)  # simulate network call

        items = [{"id": i, "value": round(random.uniform(1, 100), 2)} for i in range(1, int(count) + 1)]
        total = sum(item["value"] for item in items)

        return self.success(
            f"Fetched {len(items)} items",
            data={"items": items, "total": round(total, 2)},
            metrics={"item_count": float(len(items)), "total_value": total},
            tags=["data-fetched"],
        )

    @step(name="Process Records", order=3, requires=["Fetch Data"],
          parallel_group="processors", description="Filters and transforms records")
    def process_records(self, ctx: WorkflowContext) -> StepResult:
        items = ctx.get_data("Fetch Data", "items") or []
        time.sleep(0.1)

        processed = [item for item in items if item["value"] > 10]
        return self.success(
            f"Processed {len(processed)} of {len(items)} records",
            data={"processed": processed},
            metrics={"processed_count": float(len(processed)), "filter_rate": len(processed) / max(len(items), 1)},
            tags=["processed"],
        )

    @step(name="Generate Report", order=3, requires=["Fetch Data"],
          parallel_group="processors", description="Builds a summary report")
    def generate_report(self, ctx: WorkflowContext) -> StepResult:
        items = ctx.get_data("Fetch Data", "items") or []
        total = ctx.get_data("Fetch Data", "total") or 0.0
        name = ctx.get_data("Validate Input", "validated_name") or ctx["name"]
        time.sleep(0.1)

        avg = total / len(items) if items else 0
        report = {
            "recipient": name,
            "item_count": len(items),
            "total_value": round(total, 2),
            "average_value": round(avg, 2),
            "environment": ctx.get("environment", "development"),
        }
        return self.success(
            "Report generated",
            data={"report": report},
            metrics={"average_value": avg},
            tags=["report"],
        )

    @step(name="Send Notification", order=4,
          requires=["Process Records", "Generate Report"],
          description="Optionally sends a notification")
    def send_notification(self, ctx: WorkflowContext) -> StepResult:
        should_notify = ctx.get("notify", False)
        name = ctx.get_data("Validate Input", "validated_name") or ctx["name"]

        if not should_notify:
            return self.skip("Notification skipped — notify=False")

        # Simulate notification
        time.sleep(0.05)
        return self.success(
            f"Notification sent to {name}",
            tags=["notified"],
            metrics={"notifications_sent": 1.0},
        )
