# Claude Code Instructions

Claude Code must use [`AGENTS.md`](./AGENTS.md) as its primary context and master source of truth for all coding, architectural decisions, and repository standards.

👉 **Master Specification: [`AGENTS.md`](./AGENTS.md)**

### Quick Reference:
- **Project**: ValiantFlow Python Workflow Automation & Orchestration Platform (PyPI: `valiantflow`, v0.0.1)
- **Backend**: FastAPI, Typer, Rich, SQLAlchemy 2.0, Pydantic v2
- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS 3.4
- **Databases**: Strict SQLite file isolation per environment (`valiant_{env}.db`)
- **Primary Commands**:
  - Run Server: `valiant serve --host 0.0.0.0 --port 8000` (or `valiantflow serve`)
  - CLI Run: `valiant run <workflow_name> --env dev` (or `valiantflow run ...`)
  - CLI Logs: `valiant logs <run_id> --env dev --follow`
  - Standalone Report: `valiant report <run_id> --env dev --output report.html --open` (Multi-tab self-contained HTML with dark/light mode, tabular search/sort, governance trail, and raw logs)
  - Tests: `pytest`
  - Frontend Build: `cd frontend && npm run build`
  - Frontend Lint: `cd frontend && npm run lint`
  - Scaffold Workflow: `valiant new <name> --style compact` (or `--style functional`)
- **Workflow Authoring**: Dual authoring modes supported:
  - **Modern Compact Class**: Type-annotated class attributes (Pydantic style), auto-inferred inputs, auto step ordering, and parameter injection.
  - **Functional Micro-Workflow**: Fluent syntax `wf = workflow("name")`, `@wf.step`, `@wf.approval` with auto result wrapping (Polars DataFrames, dicts, strings, booleans, None).
- **Desktop Automation**: Uses `context.exec` (streaming subprocess with Windows `shutil.which` support), `context.poll_until` (non-blocking async polling), per-run `.log` files at `.valiant/logs/{env}/{run_id}.log`, and built-in DevOps tools (`GitHelper`, `MavenHelper`, `DockerHelper`).
- **Reports & Governance**: Self-contained 5-tab HTML reports (`Overview`, `Step Breakdown`, `Tabular Datasets`, `Governance Trail`, `Logs & Context`) with zero external CDNs, theme toggle, and print-to-PDF.
- **PR-Only Contribution Policy**: Direct pushes to `main` are strictly prohibited. All go-forward changes must be committed on a feature/bugfix branch and submitted via GitHub Pull Request (`gh pr create`).
- **Safety & QA**: Adhere strictly to the **Mandatory Testing & Quality Assurance Checklist** and **Safety & Boundaries ("Never Do" List)** in [`AGENTS.md`](./AGENTS.md). All PRs/features require 100% test pass rate, clean builds, zero Pandas, and visual snapshot reviews.
