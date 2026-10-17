# 🚀 ValiantFlow — Workflow Automation Platform

ValiantFlow is a **developer-first Python Workflow Automation & Orchestration Platform** built for simplicity, high performance, and enterprise reliability (published on PyPI as [`valiantflow`](https://pypi.org/project/valiantflow/)). Define complex multi-step automated workflows with Python decorators, execute them via CLI, Web UI, or REST API, and monitor live step-by-step executions in real-time.

> [!NOTE]
> **Public Beta (v0.0.1)**: ValiantFlow is currently in active public beta. All workflows, execution engine primitives, and web dashboard features are fully operational. Contributions, issues, and feature requests are welcomed!

---

## ✨ Features

- **⚡ Modern Unified Stack**: Single repository containing a robust FastAPI backend, SQLite audit persistence, and a high-end React + Tailwind CSS dashboard.
- **🎯 Clean Python SDK**: Author workflows with simple `@workflow` and `@step` decorators.
- **🔄 Parallel & Dependent Steps**: Run tasks in parallel (`parallel_group`), chain dependencies (`requires`), set timeouts, and configure auto-retries.
- **🌐 Multi-Environment Partitioning**: Completely isolated SQLite engines per environment (`DEV`, `UAT`, `PROD`) with presets and production guardrails.
- **🧠 Live Data Lineage & Context Diff**: Visual step-level mutation tracking showing keys added, modified, deleted, and reads, plus upstream producers and downstream consumers.
- **📊 Side-by-Side Run Comparator**: Regression diffing engine comparing baseline vs target runs across environments with latency drift, step regression matrices, and context diffs.
- **⏰ Scheduled Crons & Inbound Webhooks**: In-process `AsyncScheduler` background engine supporting 5-field cron cadences (`croniter`) and authenticated HTTP inbound webhooks (`X-Valiant-Secret`) with parameter mapping.
- **🛡️ Human-in-the-Loop Breakpoints**: Pause sensitive infrastructure runs before destructive operations, awaiting authorized approval or rejection with audit justification.
- **🖥️ Desktop Local DevOps Automation**: Native async subprocess execution engine via `context.exec(...)` with live WebSocket console streaming, binary auto-resolution (`shutil.which` for Windows `.cmd`/`.bat`), responsive process tree cancellation (`taskkill /F /T` on Windows, `os.killpg` on POSIX), and async non-blocking deployment polling via `context.poll_until(...)`.
- **📁 Dedicated Per-Run File Logging**: Isolated raw untruncated log files written directly to `.valiant/logs/{env}/{run_id}.log`, viewable/streamable via CLI (`valiant logs <run_id> --follow`) and 1-click UI Raw Log actions.
- **🛠️ Built-in DevOps Tooling Suite**: Out-of-the-box helper utilities for multi-repo branch management (`GitHelper`), POM versioning (`MavenHelper`), and base image updates (`DockerHelper`).
- **📊 First-Class Tabular Data (Polars Exclusively)**: Native support for SQL query results, high-throughput datasets, and analytics transformations powered strictly by Polars (zero Pandas). Dual-tier architecture (compact UI preview + zero-copy Parquet artifact caching), instant (<5ms) lazy in-drawer search/sort/pagination, and 1-click downloads (`CSV`, `Parquet`, `JSON`).
- **📑 Standalone Multi-Tab HTML Execution & Audit Reports**: Single-click offline-ready interactive reports with zero external dependencies, embedded CSS/SVGs, 5 tabs (Executive Overview with duration distribution bar, Step Breakdown with Expanders and filter pills, Polars Tabular Datasets with live client-side search/sort/CSV copy, Governance Audit Trail with verification seal, and Raw Logs Monospace Terminal & Masked Context JSON), Dark/Light theme switch, and browser-native print-to-PDF (`@media print`).
- **👁️ Client Template Filtering**: One-click UI toggle to hide or show built-in default templates (`Show/Hide Default Templates`) with persistent local storage, keeping the catalog clean for custom workflows while preserving templates for AI agents to inspect and author.
- **🔴 Real-Time Live Streaming**: Watch steps execute in real-time over WebSockets with live progress bars, spinners, and log consoles.
- **🔒 Sensitive Secret Masking**: Passwords, API tokens, and credentials are automatically redacted in DB history and API responses.
- **💻 Rich CLI Tool**: Run, list, inspect, report, stream logs, and scaffold workflows directly from the terminal via `valiant` or `valiantflow` (`valiant run`, `valiant list`, `valiant runs`, `valiant logs`, `valiant report`, `valiant new`).

---

## 🏗️ Architecture

```
valiant/
├── pyproject.toml              # Modern Python packaging & CLI entry points
├── run.py                      # Root CLI launcher
├── backend/
│   ├── valiant/
│   │   ├── core/               # Base Workflow, runner, models, registry, context
│   │   ├── db/                 # SQLite persistence & audit models
│   │   ├── api/                # FastAPI routers (workflows, runs, websockets)
│   │   └── cli/                # Typer CLI application
│   └── workflows/              # Workflow definitions (demo, user_management, data_pipeline)
└── frontend/                   # Modern React + Vite + Tailwind CSS dashboard
    ├── src/                    # Components (StepTimeline, DynamicForm, RunHistory)
    └── dist/                   # Production build assets served directly by FastAPI
```

---

## 🚀 Quick Start (3 Steps)

### 1. Installation

**Option A: Install from PyPI**
```bash
pip install valiantflow
```

**Option B: Local Development Clone**
```bash
# Create and activate virtual environment (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Build the React web dashboard (for local dev)
cd frontend && npm install && npm run build && cd ..
```

### 2. Launch Platform
```bash
# Start the full platform (FastAPI + Web Dashboard)
valiant serve

# Or using the valiantflow alias
valiantflow serve
```

- **Web Dashboard**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger REST API & Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 💻 Terminal CLI Usage

```bash
# 1. List all discovered workflows
valiant list

# 2. Run a workflow with parameters in a specific environment
valiant run demo --env dev --set user_name="Alice" --set max_items=50

# 3. View persistent run history from database
valiant runs --env dev --limit 10

# 4. Stream or tail dedicated per-run execution logs
valiant logs <run_id> --env dev --follow

# 5. Generate standalone self-contained HTML audit report
valiant report <run_id> --env dev --output report.html --open

# 6. Scaffold a new workflow file instantly
valiant new my_automation
```

---

---

## 📂 Workflow Locations & Automatic Discovery

When you install ValiantFlow in your own project, how does it discover your custom workflows?

### 1. Standard Discovery Convention (`./workflows/`)
By default, ValiantFlow automatically discovers all `.py` files inside a **`workflows/`** folder in your current working directory:
```bash
my-project/
├── workflows/
│   ├── data_pipeline.py
│   └── user_sync.py
```

### 2. Instant Scaffolding
Run `valiant new` in your terminal to generate a ready-to-run template in your `workflows/` directory:
```bash
# Scaffolds a new workflow into ./workflows/order_fulfillment.py
valiant new order_fulfillment
```

### 3. Custom Directory via Environment Variable
If you keep your workflows in a custom location, point `VALIANT_WORKFLOWS_DIR` to your directory:
```bash
export VALIANT_WORKFLOWS_DIR=/path/to/my/custom/workflows
valiant list
valiant serve
```

### 4. Discovery Search Priority
ValiantFlow scans the following locations automatically:
1. `$VALIANT_WORKFLOWS_DIR` (if set)
2. `./workflows/*.py` (recommended project standard)
3. `./backend/workflows/*.py` (full-stack application standard)
4. Current directory `./*.py`

In the Web UI (`http://localhost:8000/`), your custom workflows appear in the catalog. You can toggle **"Hide Default Templates"** to focus purely on your custom automations!

---

## 📝 Authoring a Workflow

Import directly from `valiantflow` (or `valiant`):

### Option A: Functional Micro-Workflow (Minimal Code)
```python
from valiantflow import workflow
import polars as pl

wf = workflow("telemetry_pipeline", description="Process and verify system telemetry")

@wf.step("Ingest Records")
def ingest(batch_id: str = "BATCH-01", count: int = 50):
    # Parameters auto-injected from inputs! Return strings, dicts, or DataFrames directly.
    return f"Ingested {count} records for batch {batch_id}"

@wf.approval("Operator Gate", prompt="Review telemetry before publishing?")
def signoff():
    pass

@wf.step("Generate Polars Report")
def report(count: int = 50):
    # Polars DataFrames are auto-wrapped into dual-tier interactive tables & Parquet artifacts!
    return pl.DataFrame({
        "device_id": [f"DEV-{i}" for i in range(count)],
        "status": ["healthy" if i % 4 != 0 else "degraded" for i in range(count)],
    })
```

### Option B: Modern Compact Class (Zero InputField Ceremony)
```python
from typing import Literal
from valiantflow import Workflow, step, workflow

@workflow(name="customer_onboarding", description="Onboard new customer and setup workspace")
class CustomerOnboardingWorkflow(Workflow):
    name = "Customer Onboarding"
    tags = ["customers", "onboarding"]

    # Type-annotated class attributes automatically generate UI forms and validation schemas:
    customer_name: str
    admin_email: str
    tier: Literal["standard", "enterprise"] = "standard"
    send_welcome: bool = True

    @step("Validate Customer")
    def validate_customer(self, customer_name: str):
        # Auto-injected parameter
        return f"Customer '{customer_name}' verified"

    @step("Create Workspace")
    def create_workspace(self, ctx):
        ctx["workspace_id"] = "ws_84920"
        return "Workspace provisioned on AWS"

    @step("Send Welcome Email", condition="send_welcome")
    def send_welcome_email(self, admin_email: str):
        return f"Welcome kit sent to {admin_email}"
```

---

## 🌐 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/workflows` | List all available workflows and input schemas |
| `GET` | `/api/workflows/{id}` | Get workflow metadata and step definitions |
| `POST` | `/api/runs` | Trigger a workflow execution (`sync` or `async`) |
| `GET` | `/api/runs` | Query execution history with pagination |
| `GET` | `/api/runs/{id}` | Inspect a specific run with step outputs & logs |
| `POST` | `/api/runs/{id}/cancel` | Cancel an active in-flight run |
| `WS` | `/api/ws/runs/{id}` | WebSocket stream for live step events & logs |

---

## 📄 License
MIT
