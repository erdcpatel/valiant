"""Valiant CLI — run, list, history, serve."""
from __future__ import annotations

import json
import sys
from typing import Annotated, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from valiant.logging_setup import configure_logging

app = typer.Typer(
    name="valiant",
    help="Valiant Workflow Automation Platform v3",
    add_completion=False,
    pretty_exceptions_enable=False,
)
console = Console()
err_console = Console(stderr=True)


def _bootstrap() -> None:
    """Load settings, logging, DB, and workflows before any command runs."""
    configure_logging()
    from valiant.storage import init_db
    from valiant.core.registry import registry
    init_db()
    registry.load_builtins()
    for d in __import__("valiant.config", fromlist=["settings"]).settings.extra_workflow_dirs:
        registry.load_directory(d)


# ── run ───────────────────────────────────────────────────────────────────────

@app.command()
def run(
    workflow_name: Annotated[str, typer.Argument(help="Workflow name to execute")],
    set_values: Annotated[
        Optional[list[str]],
        typer.Option("--set", "-s", help="Set input values as key=value (repeatable)"),
    ] = None,
    output: Annotated[str, typer.Option(help="Output format: table | json")] = "table",
    triggered_by: str = "cli",
):
    """Execute a workflow."""
    _bootstrap()

    from valiant.core.registry import registry
    from valiant.core.runner import WorkflowRunner
    from valiant.core.exceptions import WorkflowNotFoundError, WorkflowValidationError
    from valiant.core.models import StepResult, WorkflowResult
    from valiant.storage import RunRepository, get_session

    # Parse --set key=value pairs
    inputs: dict = {}
    for kv in (set_values or []):
        if "=" not in kv:
            err_console.print(f"[red]Invalid --set value '{kv}'. Use key=value format.[/red]")
            raise typer.Exit(1)
        k, v = kv.split("=", 1)
        # Coerce booleans and numbers
        if v.lower() in ("true", "yes"):
            v = True  # type: ignore[assignment]
        elif v.lower() in ("false", "no"):
            v = False  # type: ignore[assignment]
        else:
            try:
                v = int(v)  # type: ignore[assignment]
            except ValueError:
                try:
                    v = float(v)  # type: ignore[assignment]
                except ValueError:
                    pass
        inputs[k] = v

    try:
        workflow_cls = registry.get_class(workflow_name)
    except WorkflowNotFoundError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    # Stream execution with live progress
    runner = WorkflowRunner()
    result: WorkflowResult | None = None

    with console.status(f"[bold cyan]Running {workflow_name}…[/bold cyan]"):
        try:
            for item in runner.run_streaming(workflow_cls, inputs, triggered_by=triggered_by):
                if isinstance(item, StepResult):
                    icon = "✅" if item.success and not item.skipped else ("⏭️" if item.skipped else "❌")
                    console.print(f"  {icon}  [bold]{item.name}[/bold] — {item.message}  "
                                  f"[dim]{item.duration_ms:.0f}ms[/dim]")
                elif isinstance(item, WorkflowResult):
                    result = item
        except WorkflowValidationError as exc:
            err_console.print(f"[red]Validation error: {exc}[/red]")
            raise typer.Exit(1)
        except Exception as exc:
            err_console.print(f"[red]Workflow failed: {exc}[/red]")
            raise typer.Exit(1)

    if result is None:
        err_console.print("[red]No result returned.[/red]")
        raise typer.Exit(1)

    # Persist result
    session_gen = get_session()
    session = next(session_gen)
    try:
        repo = RunRepository(session)
        sensitive = {f.name for f in registry.get_meta(workflow_name).input_fields if f.sensitive}
        repo.save_with_inputs(result, inputs, sensitive)
    except Exception:
        pass
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass

    if output == "json":
        rprint(json.dumps({
            "run_id": result.run_id,
            "workflow": result.workflow_name,
            "status": result.status_label,
            "duration_ms": round(result.total_duration_ms, 1),
            "steps": [s.to_display_dict() for s in result.steps],
        }, indent=2))
        return

    # Table output
    console.print()
    status_colour = "green" if result.success else ("yellow" if result.status_label == "partial" else "red")
    console.print(
        f"[bold]Run ID:[/bold] {result.run_id[:12]}…  "
        f"[bold]Status:[/bold] [{status_colour}]{result.status_label.upper()}[/{status_colour}]  "
        f"[bold]Duration:[/bold] {result.total_duration_ms:.0f}ms"
    )

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("Step")
    table.add_column("Status")
    table.add_column("Message")
    table.add_column("Duration", justify="right")
    table.add_column("Metrics")

    for s in result.steps:
        icon = "✅" if s.success and not s.skipped else ("⏭️" if s.skipped else "❌")
        metrics_str = ", ".join(f"{k}={v}" for k, v in s.metrics.items()) if s.metrics else "—"
        table.add_row(s.name, f"{icon} {s.status_label}", s.message, f"{s.duration_ms:.0f}ms", metrics_str)

    console.print(table)

    if not result.success and result.status_label != "partial":
        raise typer.Exit(1)


# ── list ──────────────────────────────────────────────────────────────────────

@app.command(name="list")
def list_workflows(
    output: Annotated[str, typer.Option(help="Output format: table | json")] = "table",
):
    """List all registered workflows."""
    _bootstrap()
    from valiant.core.registry import registry

    if output == "json":
        data = [
            {
                "name": m.name,
                "description": m.description,
                "tags": m.tags,
                "version": m.version,
                "steps": len(m.input_fields),
            }
            for m in registry.list_meta()
        ]
        rprint(json.dumps(data, indent=2))
        return

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Tags")
    table.add_column("Version")
    table.add_column("Inputs", justify="right")

    for m in registry.list_meta():
        table.add_row(
            m.name,
            m.description or "—",
            ", ".join(m.tags) if m.tags else "—",
            m.version,
            str(len(m.input_fields)),
        )

    console.print(table)


# ── history ───────────────────────────────────────────────────────────────────

@app.command()
def history(
    workflow: Annotated[Optional[str], typer.Option(help="Filter by workflow name")] = None,
    status: Annotated[Optional[str], typer.Option(help="Filter by status")] = None,
    limit: int = 20,
    output: str = "table",
):
    """Show workflow execution history."""
    _bootstrap()
    from valiant.storage import RunRepository, get_session

    session_gen = get_session()
    session = next(session_gen)
    try:
        repo = RunRepository(session)
        runs = repo.list_runs(workflow_name=workflow, status=status, limit=limit)
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass

    if output == "json":
        rprint(json.dumps([r.to_dict() for r in runs], indent=2, default=str))
        return

    if not runs:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("Run ID")
    table.add_column("Workflow", style="bold")
    table.add_column("Status")
    table.add_column("Triggered By")
    table.add_column("Started At")
    table.add_column("Duration", justify="right")

    colours = {"success": "green", "partial": "yellow", "failed": "red", "running": "cyan"}
    for r in runs:
        c = colours.get(r.status, "white")
        started = r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else "—"
        table.add_row(
            r.run_id[:12] + "…",
            r.workflow_name,
            f"[{c}]{r.status}[/{c}]",
            r.triggered_by,
            started,
            f"{r.duration_ms:.0f}ms",
        )

    console.print(table)


# ── serve ─────────────────────────────────────────────────────────────────────

@app.command()
def serve(
    api_only: bool = False,
    ui_only: bool = False,
    api_port: int = 8000,
    ui_port: int = 8501,
    reload: bool = False,
):
    """Start the API server and/or the Taipy UI."""
    configure_logging()

    import subprocess
    import threading

    def run_api() -> None:
        import uvicorn
        uvicorn.run(
            "valiant.api.app:app",
            host="0.0.0.0",
            port=api_port,
            reload=reload,
        )

    def run_ui_proc() -> None:
        from valiant.ui.app import run_ui
        run_ui(port=ui_port)

    threads = []
    if not ui_only:
        console.print(f"[bold cyan]Starting API on http://0.0.0.0:{api_port}[/bold cyan]  (docs: /docs)")
        t = threading.Thread(target=run_api, daemon=True)
        t.start()
        threads.append(t)

    if not api_only:
        console.print(f"[bold cyan]Starting UI  on http://0.0.0.0:{ui_port}[/bold cyan]")
        t = threading.Thread(target=run_ui_proc, daemon=True)
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        console.print("\n[dim]Shutting down.[/dim]")
