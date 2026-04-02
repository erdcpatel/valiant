# Valiant — Workflow Automation Platform v3

Production-ready, Python-native workflow automation with a clean decorator API, persistent execution history, REST API, Taipy web UI, and CLI.

---

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Copy env template
cp .env.example .env

# Run the demo workflow
python main.py run demo --set name="Alice" --set count=5 --set environment=development

# List all workflows
python main.py list

# View execution history
python main.py history

# Start API + UI
python main.py serve
```

---

## Writing a Workflow

```python
from valiant import Workflow, step, workflow, InputField, InputType

@workflow(name="greet", description="Simple greeting workflow")
class GreetWorkflow(Workflow):

    def get_input_fields(self):
        return [
            InputField(name="name",  label="Your Name", required=True),
            InputField(name="shout", label="Shout it?", type=InputType.BOOLEAN, default=False),
        ]

    @step(name="Greet", order=1)
    def greet(self, ctx):
        msg = f"Hello, {ctx['name']}!"
        if ctx.get("shout"):
            msg = msg.upper()
        return self.success(msg, metrics={"length": len(msg)}, tags=["greeted"])
```

Save to `my_workflows/greet.py` then run:
```bash
VALIANT_WORKFLOW_DIRS=./my_workflows python main.py run greet --set name=Alice
```

---

## CLI Reference

```bash
python main.py run   <workflow> [--set key=value]...  # Execute a workflow
python main.py list                                    # List registered workflows
python main.py history [--workflow name] [--limit 20] # Show run history
python main.py serve [--api-only] [--ui-only]          # Start API and/or UI
```

---

## REST API

Start the API:
```bash
python main.py serve --api-only
# Docs: http://localhost:8000/docs
```

```bash
# List workflows
curl http://localhost:8000/workflows

# Run a workflow
curl -X POST http://localhost:8000/runs/demo \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -d '{"name": "Alice", "count": 3, "environment": "staging"}'

# View run history
curl http://localhost:8000/runs \
  -H "X-API-Key: dev-key-change-me-in-production"
```

Set `VALIANT_API_KEYS=key1,key2` to enable authentication (disabled when unset in dev).

---

## Web UI (Taipy)

```bash
pip install taipy-gui
python main.py serve --ui-only
# Open http://localhost:8501
```

Pages:
- **Dashboard** — run stats and recent history
- **Workflows** — browse, configure, and execute workflows with live step streaming
- **History** — paginated execution history with filters

---

## Configuration

All config via environment variables (or `.env` file):

| Variable | Default | Description |
|---|---|---|
| `VALIANT_DATABASE_URL` | `sqlite:///./valiant.db` | SQLite or PostgreSQL URL |
| `VALIANT_API_KEYS` | *(empty = no auth)* | Comma-separated valid API keys |
| `VALIANT_ALLOWED_ORIGINS` | `http://localhost:8501` | CORS allowed origins |
| `VALIANT_API_PORT` | `8000` | FastAPI port |
| `VALIANT_UI_PORT` | `8501` | Taipy UI port |
| `VALIANT_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `VALIANT_LOG_FORMAT` | `console` | `console` or `json` (for prod) |
| `VALIANT_WORKFLOW_DIRS` | *(empty)* | Extra dirs to scan for workflows |

---

## Project Structure

```
src/valiant/
├── core/          ← workflow engine: @step, @workflow, runner, registry
├── storage/       ← SQLModel persistence (WorkflowRun, StepRun)
├── api/           ← FastAPI REST API with auth and typed schemas
├── ui/            ← Taipy GUI (dashboard, workflows, history)
├── cli/           ← Typer CLI
├── config/        ← pydantic-settings
└── workflows/     ← built-in example workflows (demo, user_management)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web UI | Taipy GUI |
| REST API | FastAPI + Pydantic v2 |
| CLI | Typer + Rich |
| ORM / DB | SQLModel + SQLAlchemy 2.x |
| Data | Polars |
| Config | pydantic-settings |
| Logging | structlog |
| Python | 3.11+ |
