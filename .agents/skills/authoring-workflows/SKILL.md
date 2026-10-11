---
name: authoring-workflows
description: Authoring, scaffolding, testing, and managing Valiant workflows
---

# Authoring Valiant Workflows Guide

This skill is the definitive reference for creating, modifying, and testing workflows on the **Valiant** orchestration platform. It explains the workflow model, SDK decorators, data flow conventions, and integration features (Polars tabular data, manual approvals, parallel execution, and secret masking).

---

## 1. Anatomy of a Valiant Workflow

Every Valiant workflow is a Python class inheriting from `valiant.Workflow` and decorated with `@workflow`:

```python
"""
Order Fulfillment Workflow
"""
from backend.valiant import Workflow, step, workflow, InputField, InputType
import polars as pl


@workflow(
    name="order_fulfillment",
    description="Processes and reconciles incoming e-commerce orders"
)
class OrderFulfillmentWorkflow(Workflow):
    name = "Order Fulfillment Pipeline"
    description = "Validate inventory, process payments, and generate fulfillment report"
    version = "1.0.0"
    tags = ["orders", "finance", "e-commerce"]

    def inputs(self):
        """Define typed parameters configurable via CLI, API, or UI form."""
        return [
            InputField(
                name="batch_id",
                type=InputType.TEXT,
                required=True,
                default="BATCH-2026-001",
                label="Batch Identifier",
                help_text="Unique identifier for order batch"
            ),
            InputField(
                name="max_orders",
                type=InputType.NUMBER,
                default=100,
                min_value=1,
                max_value=10000,
                label="Max Orders",
                help_text="Cap on the number of orders to process"
            ),
            InputField(
                name="api_token",
                type=InputType.PASSWORD,
                required=False,
                sensitive=True,
                label="Payment Gateway Token",
                help_text="Encrypted secret key for payment API"
            ),
            InputField(
                name="notify_slack",
                type=InputType.CHECKBOX,
                default=True,
                label="Notify Slack Channel",
                help_text="Send completion summary to operations channel"
            )
        ]

    @step("Validate Inventory & Stock", order=1, tags=["inventory"])
    def validate_inventory(self, context):
        batch_id = context.get("batch_id")
        max_orders = context.get("max_orders", 100)

        # Context updates automatically track data lineage diffs
        context["inventory_checked"] = True
        context["available_units"] = 2500

        res = self.success(f"Inventory validated for batch {batch_id}")
        res.add_metric("batch_id", batch_id)
        res.add_metric("allocated_orders", min(max_orders, 2500))
        return res

    @step(
        "Authorize Financial Settlement",
        order=2,
        requires_approval=True,
        approval_prompt="Authorize payment gateway charge and batch settlement",
        approval_roles=["finance_lead", "admin"],
        tags=["governance", "payments"]
    )
    def authorize_settlement(self, context):
        # Suspends execution before this step until approved by an operator
        return self.success("Financial settlement authorized by operator")

    @step("Process Tabular Reconciliation", order=3, tags=["analytics", "polars"])
    def reconcile_orders(self, context):
        # Tabular data MUST use Polars exclusively (NEVER Pandas)
        df = pl.DataFrame({
            "order_id": ["ORD-101", "ORD-102", "ORD-103", "ORD-104"],
            "amount": [129.50, 49.99, 399.00, 15.00],
            "status": ["settled", "settled", "review", "settled"],
            "settled": [True, True, False, True]
        })

        # Set tabular data for instant UI table previews and Parquet artifact export
        res = self.success("Reconciled 4 orders successfully")
        res.set_tabular_data(df)
        return res

    @step("Notify Slack Operations", order=4, condition="notify_slack", tags=["notification"])
    def send_notification(self, context):
        return self.success("Slack notification dispatched to #ops-fulfillment")
```

---

## 2. Core SDK Decorators & Primitives

### `@workflow(name="...", description="...")`
- Declares the unique workflow identifier in the registry.
- Class attributes:
  - `name`: Display title in UI and CLI.
  - `description`: Subtitle summary.
  - `version`: Semantic version string.
  - `tags`: List of strings for UI filtering and categorizing.

### `@step("Step Name", ...)` Options
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `order` | `int` | Sequential step execution priority (default: `1`). |
| `requires` | `List[str]` | Upstream prerequisite step names for DAG ordering. |
| `parallel_group` | `str` | Name of parallel group. Steps with the same group run concurrently via `asyncio.gather`. |
| `condition` | `str` or `Callable` | Context key or predicate function evaluated before dispatch. Skips step if falsy. |
| `requires_approval` | `bool` | Human-in-the-Loop breakpoint. Halts pipeline until operator approves or rejects. |
| `approval_prompt` | `str` | User-facing message presented to operator in approval dialog and banner. |
| `approval_roles` | `List[str]` | Authorized role list permitted to approve (e.g. `["admin", "sre"]`). |
| `tags` | `List[str]` | Operational categories (`["database", "security", "infra"]`). |

---

## 3. Tabular Data with Polars (Strict Rule)

Valiant enforces **Polars exclusively** for all tabular data, SQL query results, and DataFrame processing:
- **NEVER use Pandas**: Pandas is strictly forbidden in this platform.
- **Dual-Tier Storage Architecture**:
  - **Tier 1 (Preview & Telemetry)**: Compact JSON payload (~15-30 KB, capped at 50 rows) embedded in `StepResult.tabular_data` for immediate UI rendering and SQLite persistence.
  - **Tier 2 (Full Parquet Artifact)**: Full un-truncated dataset saved with zero-copy write to `.valiant/artifacts/{env}/{run_id}/{step_name}.parquet`.
- **How to return tabular data from a step**:
  ```python
  import polars as pl

  @step("Fetch SQL Records", order=1)
  def fetch_records(self, context):
      df = pl.DataFrame({
          "customer_id": [1, 2, 3],
          "balance": [450.0, 1200.5, 89.0],
          "active": [True, True, False]
      })
      res = self.success(f"Loaded {len(df)} records")
      res.set_tabular_data(df)
      return res
  ```

---

## 4. Human-in-the-Loop Breakpoints & Approvals

To protect sensitive operations (e.g., cloud provisioning, schema migrations, production deployments), add `requires_approval=True` to the step decorator:

```python
@step(
    "Apply Database Migration",
    order=2,
    requires_approval=True,
    approval_prompt="Review pending schema ALTER statements before execution",
    approval_roles=["dba", "admin"]
)
def apply_migration(self, context):
    return self.success("Database migration executed successfully")
```

- When reached, the workflow safely pauses.
- The UI displays an amber breakpoint banner with one-click **"Approve & Resume"** and **"Reject Step"** actions.
- The approval audit trail (approver identity, timestamp, justification notes) is saved in database history and standalone HTML reports.

---

## 5. Workflow Discovery & Directory Conventions

The registry automatically searches for workflow `.py` files in:
1. `backend/workflows/` (platform catalog)
2. `workflows/` (root workspace directory)
3. Any directory specified by the `VALIANT_WORKFLOWS_DIR` environment variable.

### Scaffolding a New Workflow:
```bash
# Creates backend/workflows/order_sync.py
valiant new order_sync

# Creates a workflow in a custom directory
valiant new customer_audit --dir ./custom_workflows
```

### Running and Testing via CLI:
```bash
# List all discovered workflows
valiant list

# Execute workflow in DEV environment
valiant run order_fulfillment --env dev --set batch_id="BATCH-009"

# Inspect execution history
valiant runs --env dev

# Generate standalone HTML execution report
valiant report <run_id> --env dev --output report.html --open
```

---

## 6. How Default Workflows Serve Clients

When Valiant is installed or cloned, the default workflows in `backend/workflows/` serve as out-of-the-box working references:
- **`sql_query_analytics.py`**: Reference for Polars DataFrame integration, SQL querying, and Parquet caching.
- **`infrastructure_deployment.py`**: Reference for Human-in-the-Loop approval breakpoints and governance trails.
- **`api_failure_demo.py`**: Reference for error handling, diagnostics, and Smart Resumption.
- **`demo.py`**: Reference for inputs, conditional branches, and metrics.

Clients can run these default workflows immediately to verify platform health or duplicate them to build customized production automations.
