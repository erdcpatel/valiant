# ValiantFlow — AI Agent Architecture & Operating Standards (`AGENTS.md`)

This document serves as the master source of truth for all AI agents (Antigravity, GitHub Copilot, Claude Code, Cursor, and others) operating on this repository. All agent decisions, code generation, and automated refactoring must strictly adhere to the standards outlined below.

---

## 1. Project Overview & Tech Stack

**ValiantFlow** (published on PyPI as `valiantflow`, package module `valiant`, CLI entry points `valiant` and `valiantflow`) is a developer-first Python workflow automation and orchestration platform with a high-performance FastAPI engine, Typer CLI, and modern React 19 visual operations dashboard.

### Core Technologies
- **Backend**:
  - Python >= 3.10 (standardized on 3.11+)
  - **Frameworks**: FastAPI (async REST & WebSockets), Typer & Rich (terminal CLI), Pydantic v2 (models & schema validation), SQLAlchemy 2.0 (persistence & query engine)
  - **Package Management**: Setuptools / pip (`pyproject.toml`)
- **Frontend**:
  - React 19 + TypeScript (strict mode)
  - **Build & Bundling**: Vite 8, Tailwind CSS 3.4, PostCSS, Lucide React icons
  - **Linting & Code Quality**: Oxlint, TypeScript Compiler (`tsc -b`)
- **Storage & State**:
  - Isolated SQLite engines partitioned per environment (`valiant_dev.db`, `valiant_uat.db`, `valiant_prod.db`)

---

## 2. Architectural Boundaries

Strict boundaries exist between platform core, workflow definitions, API presentation, and UI assets:

```
valiant/
├── backend/
│   ├── valiant/                  # Platform Core (FRAMEWORK ENGINE ONLY)
│   │   ├── core/                 # Runner, DAG engine, Context, Registry, Environment
│   │   ├── db/                   # Multi-environment database engines & models
│   │   ├── api/                  # FastAPI routers, WebSocket handlers, static mounts
│   │   └── cli/                  # CLI command entry points (`valiant ...`)
│   └── workflows/                # Workflows Catalog (Client / Domain logic only)
├── frontend/                     # React Single-Page Application (Vite + Tailwind)
│   ├── src/components/           # Reusable UI components (DAG, Modals, History Table)
│   ├── src/pages/                # Top-level view containers (Workflows, LiveRun)
│   └── src/api.ts                # Strict HTTP/WebSocket client layer
└── .agents/                      # Agent skills and capabilities
```

### Boundary Rules:
1. **Workflows vs. Core Platform Isolation**:
   - Domain workflows MUST reside exclusively in `backend/workflows/` (or user-defined external folders).
   - Workflows inherit from `valiant.Workflow` and use `@step` decorators.
   - Workflows MUST NOT import from `backend.valiant.api` or `backend.valiant.db` directly. All workflow data flow must pass through the `WorkflowContext` (`context`) and return `self.success()`, `self.failure()`, or `self.skip()`.
2. **Environment Database Partitioning**:
   - Never cross-pollinate database files. Each environment (`dev`, `uat`, `prod`) reads and writes only to its dedicated SQLite file (`valiant_{env}.db`).
   - All DB operations must accept an explicit `env` parameter and resolve through dynamic connection managers in `backend/valiant/db/database.py`.
3. **Execution Context Lineage & Scoped Diffing**:
   - Parallel and sequential steps track mutations via `ScopedStepContext`.
   - Never expose raw secrets in step lineage or diff snapshots (`mask_secrets=True`).
   - Lineage must maintain bidirectional mapping (upstream producers to downstream consumers).
4. **Side-by-Side Run Comparator & Regression Engine**:
   - Compare runs across environments (`dev` vs `uat` vs `prod`) through `compare_runs_data` (`backend/valiant/core/comparator.py`).
   - Comparator must classify outcome drifts (`regression`, `improved`, `same`), step status drifts, latency drift (`time_delta`, `time_ratio`), and inputs/context differences cleanly without cognitive clutter.
5. **API & Route Boundary**:
   - HTTP route handlers in `backend/valiant/api/routers/` must only handle request validation, environment header resolution (`X-Valiant-Env`), and runner delegation. No workflow business logic belongs in route handlers.
6. **Frontend Boundary**:
   - All backend communication in the frontend MUST go through `frontend/src/api.ts`.
   - The active environment header (`X-Valiant-Env`) must be propagated to all API calls.
7. **Automation & In-Process Scheduler Boundary**:
   - Scheduled crons and inbound webhooks execute within the in-process `AsyncScheduler` worker without external dependencies (no Celery/Redis).
   - Cron timers evaluate against UTC timestamps using `croniter`.
   - Webhooks authenticate via path token and optional `X-Valiant-Secret` headers. Inbound HTTP requests return `202 Accepted` immediately and delegate workflow execution asynchronously to `WorkflowRunner`.
8. **Human-in-the-Loop Breakpoints & Manual Approvals**:
   - Steps requiring manual authorization use `@step(requires_approval=True, approval_prompt="...", approval_roles=[...])`.
   - The runner suspends execution before step dispatch, emits `STEP_WAITING_APPROVAL`, and pauses asynchronously via `asyncio.Event` without blocking worker threads.
   - Resumption is dual-mode: active in-flight executions are signaled directly via memory event (`_APPROVAL_EVENTS`), while persistent suspended runs resume execution through isolated SQLite state.
   - Rejection halts downstream execution safely, marks step status as `REJECTED`, and captures operator justification in database audit trails.
9. **First-Class Tabular Data Engine (Polars Exclusively)**:
   - All tabular data transformations, database query results, and tabular workflow outputs MUST use **Polars** (`polars.DataFrame`, `polars.LazyFrame`). **NEVER use Pandas**.
   - Dual-tier storage architecture guarantees optimal memory and WebSocket latency:
     - **Tier 1 (Preview & Telemetry)**: Fast compact preview payload (~15-30 KB, capped at 50 rows) embedded in `StepResult.tabular_data` for immediate UI rendering and SQLite persistence.
     - **Tier 2 (Full Parquet Artifact)**: Full un-truncated dataset saved with zero-copy write to `.valiant/artifacts/{env}/{run_id}/{step_name}.parquet`.
   - Dedicated lazy scan query API (`GET /api/runs/{run_id}/steps/{step_name}/tabular/data`) powers instantaneous (<5ms) in-drawer filtering, column sorting, text search, and pagination directly from memory-mapped Parquet.
   - Dedicated streaming export API (`GET /api/runs/{run_id}/steps/{step_name}/tabular/export`) streams full datasets as `CSV`, `Parquet`, or `JSON` with 1-click downloads.
10. **Standalone Multi-Tab HTML Execution & Audit Report Generator**:
    - Generates self-contained, offline-ready HTML reports for any workflow run via `backend/valiant/core/report.py`.
    - HTML reports require zero external CDNs, scripts, or fonts. Everything is self-contained with embedded CSS variables, SVGs, and lightweight vanilla JS.
    - Features 5 interactive tabs:
      - 📊 **Executive Overview & Topology**: Run metadata, KPI summary cards, execution duration percentage timeline bar, and masked workflow inputs grid.
      - ⚡ **Step Execution Breakdown**: Status filter pills (`All`, `Succeeded`, `Failed`, `Approvals`, `Tabular`), Expand/Collapse all controls, and collapsible step accordions with duration, diagnostics, context deltas, and step logs.
      - 📈 **Polars Tabular Datasets**: Dataset switcher, live client-side search across all columns, clickable column sorting (ascending/descending), and CSV clipboard copy.
      - 🛡️ **Governance Audit Trail**: Official compliance seal banner, human-in-the-loop authorization gates, operator identities, timestamps, and justification trails.
      - 📜 **Raw Execution Logs & Final Context**: Terminal console viewer displaying full untruncated disk logs (`.valiant/logs/{env}/{run_id}.log`) and formatted context JSON with automated secret masking (`********`).
    - Interactive controls: Dark/Light mode theme toggle switch with persistent storage, HTML file download, and native print-to-PDF (`@media print` stylesheet automatically expands all tabs and accordions for complete paper/PDF documentation).
    - Accessible via CLI (`valiant report <run_id> --output path --open`), REST API (`GET /api/runs/{run_id}/report/html?download=bool`), and 1-click actions in Live Run header, Run Details modal, and Run History table.
11. **Desktop Local DevOps Automation & Subprocess Execution Engine**:
    - Subprocess execution must always use `await context.exec(command, cwd=..., env=..., timeout=..., stream_logs=True)`.
    - Cross-platform binary resolution (`shutil.which`) is enforced so Windows batch scripts (`mvn.cmd`, `npm.cmd`) resolve cleanly without platform-specific code.
    - Responsive cancellation: When a run is cancelled, active child processes are immediately terminated via process tree killing (`taskkill /F /T` on Windows, `os.killpg` on Unix).
    - Dedicated per-run raw execution log files are stored at `.valiant/logs/{env}/{run_id}.log` with zero line drops, accessible via CLI (`valiant logs <run_id> --follow`), REST API (`GET /api/runs/{run_id}/logs/file`), and UI 1-click download split-buttons.
    - Long-running async deployment checks must use `await context.poll_until(check_target, predicate=..., timeout=..., interval=...)` with live progress heartbeats emitted to UI.
    - Reusable DevOps helpers reside in `backend/valiant/tools/` (`GitHelper`, `MavenHelper`, `DockerHelper`).
12. **Client-Side Compact & Functional Micro-Workflow Engine**:
    - **Dual Syntax Support**: Workflows may be authored as modern type-annotated classes (Pydantic/Dataclass-style with auto-inferred inputs and auto step ordering) or fluent functional micro-workflows (`wf = workflow(...)`, `@wf.step`, `@wf.approval`).
    - **Direct Parameter Injection**: Step functions declare required parameters directly (`def step(batch_id: str, count: int, ctx=None):`); the runner auto-resolves arguments from workflow inputs and execution context.
    - **Automatic Result Wrapping**: Step functions can directly return Polars DataFrames (auto-captured as dual-tier Parquet artifacts), dictionaries, strings, booleans, or `None` without boilerplate `self.success(...)` calls.
    - **Backward Compatibility**: Fully backward compatible with legacy `Workflow` subclasses and explicit `InputField` definitions.
13. **Default Template Filtering & Zero-Refactoring PyPI Packaging**:
    - **PyPI Distribution Identity**: Distributed on PyPI as `valiantflow` (`pip install valiantflow`) with dual CLI entry points (`valiant` and `valiantflow`). Internal Python imports remain `import valiant` or `from backend.valiant import ...` with zero breaking refactoring.
    - **Built-in Template Isolation**: Workflows discovered from `backend/workflows/` or declaring `is_default=True` are tagged with `"is_default": True`. They remain permanently in the codebase so AI agents can inspect and author new workflows.
    - **Client Catalog Toggle**: The UI provides a 1-click toggle button (`Hide / Show Built-in Templates`) with client-side persistence in `localStorage`, and the REST API supports `include_defaults=bool` (or `VALIANT_HIDE_DEFAULTS=1` env var) so clients can work with only custom domain workflows.

---

## 3. Mandatory Testing & Quality Assurance Checklist

Every feature addition or refactoring must strictly satisfy this checklist:
1. **Automated Pytest Suite**: Execute `pytest tests/` (100% passing across all suites).
2. **Frontend Type Checking & Bundling**: Execute `cd frontend && npm run lint && npm run build` (0 TypeScript compiler errors, 0 Oxlint errors).
3. **Cross-Platform & Windows Verification**: Ensure file I/O specifies `encoding="utf-8"`, paths format via `Path.as_posix()`, and shell binaries resolve via `shutil.which`.
4. **Visual UI/UX Snapshot Review**: Capture actual browser screenshots using Playwright or system Chrome to visually audit layout, spacing, dark-mode color balance, and interactive states.
5. **Dependency Hygiene**: Verify zero unapproved dependencies are introduced. Tabular data must strictly use **Polars** (zero Pandas).
6. **Documentation & Agent Skills Sync**: Keep `AGENTS.md`, `CLAUDE.md`, `.agents/skills/authoring-workflows/SKILL.md`, and `.agents/skills/code-review/SKILL.md` synchronized with the new capabilities.

---

## 4. Code Style & Rules

### Backend (Python)
- **Typing**: Strict type annotations on all function signatures (`Optional[T]`, `Dict[str, Any]`, `List[T]`, `Union`).
- **Pydantic v2**: Use modern Pydantic v2 methods (`model_dump()`, `model_validate()`, `Field()`); NEVER use deprecated v1 methods (`.dict()`).
- **Async Safety**: Use async-first primitives for I/O and runner execution (`async def`, `await asyncio.gather(...)`).
- **Context & Secret Hygiene**: Always use `mask_secrets=True` when serializing execution context snapshots or logging output. Never expose unmasked secrets or API tokens.
- **Error Handling**: Step failures in workflows must return structured results (`self.failure("Descriptive reason")`). Let unhandled framework exceptions bubble up to the `WorkflowRunner` error handler for proper audit logging.
- **Preserve Documentation**: Retain all existing docstrings, type annotations, and comments.

### Frontend (React / TypeScript)
- **Functional Components**: React functional components with explicit TypeScript interfaces.
- **Tailwind Palette**: Respect Valiant dark-mode theme (`slate-900`, `slate-950`, `border-slate-800`, with accent colors: `sky` for general UI, `emerald` for DEV, `amber` for UAT, `rose` for PROD).
- **Responsive & Fullscreen**: Support both full desktop layouts and modal-expanded views.

---

## 4. Commands Reference

### Backend
- **Install in Editable Mode**:
  ```bash
  pip install -e .
  ```
- **Start Platform Server (FastAPI + Web UI)**:
  ```bash
  valiant serve --host 0.0.0.0 --port 8000
  ```
- **Run Workflow via CLI**:
  ```bash
  valiant run <workflow_name> --env dev
  ```
- **List Workflows / Inspect Runs**:
  ```bash
  valiant list
  valiant runs --env dev
  ```
- **Generate Standalone HTML Run Report**:
  ```bash
  valiant report <run_id> --env dev --output report.html --open
  ```
- **Run Tests**:
  ```bash
  pytest
  ```

### Frontend
- **Install Dependencies**:
  ```bash
  cd frontend && npm install
  ```
- **Development Server**:
  ```bash
  cd frontend && npm run dev
  ```
- **Build Production Assets**:
  ```bash
  cd frontend && npm run build
  ```
- **Lint Frontend**:
  ```bash
  cd frontend && npm run lint
  ```

---

## 5. Safety & Boundaries ("Never Do" List)

1. **NEVER modify existing application code** when executing architectural analysis or documentation updates unless explicitly requested by the user.
2. **NEVER perform unpartitioned or hardcoded DB operations**: Always use the environment-scoped session manager (`valiant_{env}.db`).
3. **NEVER execute raw unparameterized SQL queries**: Use SQLAlchemy Core/ORM queries or parameterized statements.
4. **NEVER log or persist raw credentials or secrets**: Always utilize the built-in secret masking helpers (`WorkflowContext.to_dict(mask_secrets=True)`).
5. **NEVER embed workflow-specific business logic into `backend/valiant/core/`**: Keep the core generic and extensible.
6. **NEVER bypass production guardrails**: Any trigger targeting the `prod` environment must enforce explicit operator authorization.
7. **NEVER commit temporary database files (`valiant_*.db`), logs, or node_modules** to git.
8. **NEVER use Pandas**: Use **Polars** exclusively for all tabular transformations, SQL result processing, and analytics workflows.
9. **NEVER push directly to `main`**: All go-forward code changes, refactoring, and feature additions MUST be created on a dedicated feature/bugfix branch and submitted via Pull Request (`gh pr create`). Direct pushes to `main` are strictly forbidden.
