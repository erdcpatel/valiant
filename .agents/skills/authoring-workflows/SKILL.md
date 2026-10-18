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
# When pip installed: from valiantflow import Workflow, step, workflow, InputField, InputType
# Or: from valiant import ... / from backend.valiant import ...
from valiantflow import Workflow, step, workflow, InputField, InputType
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

## 2. Modern Compact & Functional Workflow Authoring

Valiant provides two ultra-compact authoring paradigms that reduce boilerplate by **70–85%**:

### 2.1 Functional Micro-Workflows (Minimal Code)
Best for scripts, DevOps pipelines, and lightweight automations where defining a class is unnecessary ceremony:
```python
from backend.valiant import workflow
import polars as pl

wf = workflow("telemetry_pipeline", description="Process and verify system telemetry")

# Declare parameters (or let them auto-infer from step arguments)
wf.input("batch_id", type=str, default="BATCH-01")
wf.input("count", type=int, default=50)

@wf.step("Ingest Records")
def ingest(batch_id: str, count: int):
    # Parameters are auto-injected from inputs! Return strings directly.
    return f"Ingested {count} records for batch {batch_id}"

@wf.approval("Operator Review", prompt="Review telemetry before publishing?")
def signoff():
    pass

@wf.step("Generate Polars Report")
def report(count: int = 50):
    # Returning a Polars DataFrame automatically wraps it into a dual-tier table & Parquet artifact!
    return pl.DataFrame({
        "device_id": [f"DEV-{i}" for i in range(count)],
        "status": ["healthy" if i % 4 != 0 else "degraded" for i in range(count)],
    })
```

### 2.2 Modern Compact Classes (Pydantic / Dataclass Style)
Best for structured, reusable pipelines. Eliminate `def inputs(self)` completely by declaring type-annotated class attributes:
```python
from typing import Literal
from backend.valiant import Workflow, step, workflow

@workflow(name="customer_onboarding", description="Onboard new customer and setup workspace")
class CustomerOnboardingWorkflow(Workflow):
    name = "Customer Onboarding"
    tags = ["customers", "onboarding"]

    # Type-annotated class attributes auto-generate UI dynamic forms & validation schemas:
    customer_name: str
    admin_email: str
    tier: Literal["standard", "enterprise"] = "standard"
    send_welcome: bool = True

    @step("Validate Customer")
    def validate_customer(self, customer_name: str):
        # Auto-injected argument
        return f"Customer '{customer_name}' verified"

    @step("Create Workspace")
    def create_workspace(self, ctx):
        ctx["workspace_id"] = "ws_84920"
        return "Workspace provisioned on AWS"

    @step("Send Welcome Email", condition="send_welcome")
    def send_welcome_email(self, admin_email: str):
        return f"Welcome kit sent to {admin_email}"
```

### 2.3 Automatic Primitives & Conveniences
- **Direct Parameter Injection**: Step functions declare required arguments directly (`def step_fn(batch_id: str, ctx=None):`). The runner resolves them from workflow inputs and execution context.
- **Auto Step Sequencing**: When `order` is omitted in `@step(...)`, steps are automatically ordered based on their declaration sequence (10, 20, 30...).
- **Automatic Result Wrapping**:
  - `polars.DataFrame` ➔ Auto-captures dual-tier preview + memory-mapped Parquet artifact.
  - `str` ➔ `StepResult(success=True, message=str)`.
  - `dict` ➔ `StepResult(success=True, data=dict)`.
  - `bool` ➔ `StepResult(success=bool)`.
  - `None` ➔ `StepResult(success=True, message="Completed")`.
  - Unhandled exceptions ➔ `StepResult(success=False, error=str)`.

---

## 3. Core SDK Decorators & Primitives

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

### Scaffolding and Initializing Workflows:
```bash
# Initialize a new project with a workflows/ directory and starter template
valiant init

# Scaffolds a modern compact workflow (type-annotated, minimal boilerplate)
valiant new order_sync --style compact

# Scaffolds a functional micro-workflow (script-style, ultra-minimal)
valiant new quick_deploy --style functional

# Discover and run a specific custom workflow directory or single file
valiant list --dir ./my_workflows --no-defaults
valiant run custom_flow --dir ./my_workflows/custom_flow.py --env dev
valiant runs --env dev --limit 10

# Creates a legacy full-class workflow
valiant new audit_pipeline --style standard

# Creates a workflow in a custom directory
valiant new customer_audit --dir ./custom_workflows --style compact
```

### Running and Testing via CLI:
```bash
# List all discovered workflows
valiant list

# Execute workflow in DEV environment
valiant run order_fulfillment --env dev --set batch_id="BATCH-009"

# Inspect execution history
valiant runs --env dev

# Generate standalone multi-tab HTML execution report
valiant report <run_id> --env dev --output report.html --open
```

### Standalone Multi-Tab HTML Reports
Valiant generates 100% self-contained execution reports (zero external CDNs or remote dependencies) containing 5 interactive tabs:
- 📊 **Executive Overview**: KPI metrics cards, duration percentage timeline distribution bar, masked input parameters.
- ⚡ **Step Execution Breakdown**: Status filter pills (`All`, `Succeeded`, `Failed`, `Approvals`, `Tabular`), Expand/Collapse controls, collapsible step accordions, duration, failure diagnostics, context mutations (`+ added`, `~ modified`), and step logs.
- 📈 **Polars Tabular Datasets**: Multi-dataset switcher, client-side real-time text search, clickable column sorting, and CSV clipboard copy.
- 🛡️ **Governance Audit Trail**: Official compliance seal banner, manual authorization gate metadata, operator justifications.
- 📜 **Raw Execution Logs & Final Context**: Embedded monospace terminal viewer for `.valiant/logs/{env}/{run_id}.log` and formatted JSON context viewer with automatic secret masking (`********`).
- **Interactive Controls**: Dark/Light mode theme toggle switch, HTML file download, and native print-to-PDF (`@media print` automatically unhides all tabs and expands all accordions for full physical PDF export).
- Accessible via CLI (`valiant report <run_id>`), REST API (`GET /api/runs/{run_id}/report/html`), and 1-click split actions throughout the UI.


---

## 6. Desktop & Local DevOps Automation

Valiant provides first-class primitives for running local desktop DevOps workflows (e.g. Maven builds, Git branch creation/push, Docker container packaging, and deployment polling):

### Subprocess Execution with `context.exec`
Execute local CLI binaries with real-time WebSocket console streaming and automatic write to the run's dedicated log file:
```python
res = await context.exec(
    ["mvn", "clean", "install", "-DskipTests"],
    cwd=repo_path,
    env={"JAVA_HOME": "/usr/lib/jvm/default"}
)
if not res.ok:
    return self.failure(f"Maven build failed with exit code {res.returncode}")
```
- **Cross-Platform**: Automatically resolves binary paths via `shutil.which` (e.g. `mvn` -> `mvn.cmd` on Windows).
- **Process Group Tracking**: Tracked in `_active_processes` registry. Immediate, responsive abort via `os.killpg` on POSIX and `taskkill /F /T` on Windows.

### Non-Blocking Deployment Polling with `context.poll_until`
Wait for asynchronous deployment endpoints or external API states without blocking the worker thread:
```python
async def check_version():
    status = await fetch_service_health()
    return status.get("version") == target_version

deployed = await context.poll_until(check_version, timeout_secs=300, interval_secs=5)
if not deployed:
    return self.failure("Deployment timed out after 5 minutes")
```

### Dedicated Per-Run Log Files
Every workflow run generates an isolated raw log on disk:
- Stored at `.valiant/logs/{env}/{run_id}.log`.
- Inspected in CLI via `valiant logs <run_id> --env dev --follow`.
- Downloaded or viewed via 1-click Raw Log split-button in the Web UI.

### Built-in DevOps Helpers
Valiant includes battle-tested helper classes:
```python
from backend.valiant import GitHelper, MavenHelper, DockerHelper

# Git operations
git = GitHelper(repo_dir)
git.create_and_checkout_branch("feature/bom-5.0.0")
git.commit_and_push(commit_msg="JIRA-1234: Upgrade BOM to 5.0.0")

# Maven POM operations
mvn = MavenHelper(repo_dir)
current_ver = mvn.get_parent_bom_version()
mvn.update_parent_bom_version(new_version="5.0.0")

# Dockerfile operations
docker = DockerHelper(repo_dir)
curr_image = docker.get_base_image()
docker.update_base_image("eclipse-temurin:21-jre-alpine")
```

---

## 7. Built-in Templates & Client Catalog Isolation

When ValiantFlow is installed or cloned, default workflows in `backend/workflows/` serve as out-of-the-box working references:
- **`compact_micro_workflow.py`**: Reference for ultra-minimal functional micro-workflows (`wf = workflow(...)`), direct parameter injection, auto step sequencing, and Polars DataFrame auto-wrapping.
- **`bom_test_automation.py`**: Reference for multi-repo Git/Maven/Docker upgrade automation, desktop `context.exec`, deployment polling, dual approvals, and `mock_mode` testing.
- **`sql_query_analytics.py`**: Reference for Polars DataFrame integration, SQL querying, and Parquet caching.
- **`infrastructure_deployment.py`**: Reference for Human-in-the-Loop approval breakpoints and governance trails.
- **`api_failure_demo.py`**: Reference for error handling, diagnostics, and Smart Resumption.
- **`demo.py`**: Reference for inputs, conditional branches, and metrics.

### Client View & AI Learning Separation:
- **Permanent AI Learning Resource**: Default workflows remain in `backend/workflows/` so AI agents can inspect, learn, and author domain-specific workflows following validated platform patterns.
- **Automatic Tagging**: Discovered workflows from `backend/workflows/` (or declaring `is_default = True`) receive `"is_default": True` in their schema.
- **Client UI Toggle**: Clients can toggle "Hide Built-in Templates" in the Web UI catalog with 1 click (persisted in `localStorage`), keeping the interface focused on custom enterprise workflows.
- **API & Environment Filtering**: `GET /api/workflows?include_defaults=false` or setting `VALIANT_HIDE_DEFAULTS=1` excludes default templates from API responses.

