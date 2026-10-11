# Claude Code Instructions

Claude Code must use [`AGENTS.md`](./AGENTS.md) as its primary context and master source of truth for all coding, architectural decisions, and repository standards.

👉 **Master Specification: [`AGENTS.md`](./AGENTS.md)**

### Quick Reference:
- **Project**: Valiant Python Workflow Automation & Orchestration Platform (v3.0.0)
- **Backend**: FastAPI, Typer, Rich, SQLAlchemy 2.0, Pydantic v2
- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS 3.4
- **Databases**: Strict SQLite file isolation per environment (`valiant_{env}.db`)
- **Primary Commands**:
  - Run Server: `valiant serve --host 0.0.0.0 --port 8000`
  - CLI Run: `valiant run <workflow_name> --env dev`
  - Tests: `pytest`
  - Frontend Build: `cd frontend && npm run build`
  - Frontend Lint: `cd frontend && npm run lint`
- **Safety**: Review the **Safety & Boundaries ("Never Do" List)** in [`AGENTS.md`](./AGENTS.md) before performing modifications.
