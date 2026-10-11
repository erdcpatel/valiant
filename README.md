# 🚀 Valiant — Workflow Automation Platform

Valiant is a **developer-first Python Workflow Automation & Orchestration Platform** built for simplicity, high performance, and enterprise reliability. Define complex multi-step automated workflows with Python decorators, execute them via CLI, Web UI, or REST API, and monitor live step-by-step executions in real-time.

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
- **📊 First-Class Tabular Data (Polars Exclusively)**: Native support for SQL query results, high-throughput datasets, and analytics transformations powered strictly by Polars (zero Pandas). Dual-tier architecture (compact UI preview + zero-copy Parquet artifact caching), instant (<5ms) lazy in-drawer search/sort/pagination, and 1-click downloads (`CSV`, `Parquet`, `JSON`).
- **📑 Standalone HTML Execution & Audit Reports**: Single-click offline-ready interactive reports with zero external dependencies, embedded CSS/SVGs, browser-native print-to-PDF (`@media print`), KPI summaries, step timelines, governance approval trails, and Polars tabular data embeds.
- **🔴 Real-Time Live Streaming**: Watch steps execute in real-time over WebSockets with live progress bars, spinners, and log consoles.
- **🔒 Sensitive Secret Masking**: Passwords, API tokens, and credentials are automatically redacted in DB history and API responses.
- **💻 Rich CLI Tool**: Run, list, inspect, report, and scaffold workflows directly from the terminal (`valiant run`, `valiant list`, `valiant runs`, `valiant report`, `valiant new`).

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

### 1. Backend Setup
```bash
# Create and activate virtual environment (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate

# Install Valiant and dependencies
pip install -e .
```

### 2. Frontend Build
```bash
# Build the React web dashboard
cd frontend
npm install
npm run build
cd ..
```

### 3. Launch Platform
```bash
# Start the full platform (FastAPI + Web Dashboard)
valiant serve

# Or run via run.py
python run.py serve
```

- **Web Dashboard**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger REST API & Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 💻 Terminal CLI Usage

```bash
# 1. List all discovered workflows
valiant list

# 2. Run a workflow with parameters
valiant run demo --set user_name="Alice" --set max_items=50

# 3. View persistent run history from database
valiant runs --limit 10

# 4. Generate standalone self-contained HTML audit report
valiant report <run_id> --env dev --output report.html --open

# 5. Scaffold a new workflow file instantly
valiant new my_automation
```

---

## 📝 Authoring a Workflow

```python
from backend.valiant import Workflow, step, workflow, InputField, InputType

@workflow(name="customer_onboarding", description="Onboard new customer and setup workspace")
class CustomerOnboardingWorkflow(Workflow):
    name = "Customer Onboarding"
    description = "Provision customer accounts and workspaces"
    version = "1.0.0"
    tags = ["customers", "onboarding"]

    def inputs(self):
        return [
            InputField("customer_name", type=InputType.TEXT, required=True),
            InputField("admin_email", type=InputType.EMAIL, required=True),
            InputField("tier", type=InputType.SELECT, options=["standard", "enterprise"], default="standard"),
            InputField("send_welcome", type=InputType.CHECKBOX, default=True)
        ]

    @step("Validate Customer", order=1, tags=["validation"])
    def validate_customer(self, context):
        name = context.get("customer_name")
        res = self.success(f"Customer '{name}' verified")
        res.add_metric("name_length", len(name))
        return res

    @step("Create Workspace", order=2, requires=["Validate Customer"], tags=["cloud"])
    def create_workspace(self, context):
        context["workspace_id"] = "ws_84920"
        return self.success("Workspace provisioned on AWS")

    @step("Send Welcome Email", order=3, condition="send_welcome", requires=["Create Workspace"], tags=["email"])
    def send_welcome_email(self, context):
        email = context.get("admin_email")
        return self.success(f"Welcome kit sent to {email}")
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
