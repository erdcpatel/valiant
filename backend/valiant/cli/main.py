"""
Typer CLI implementation for Valiant.
"""
import typer
import asyncio
import os
import json
import getpass
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..core.registry import registry
from ..core.runner import WorkflowRunner
from ..core.models import StepStatus
from ..db.database import save_run_result, get_recent_runs

app = typer.Typer(help="Valiant Workflow Automation Platform CLI")
console = Console()


@app.command("list")
def list_workflows():
    """List all available workflows."""
    registry.discover()
    workflows = registry.list_workflows()

    if not workflows:
        console.print("[yellow]No workflows found.[/yellow]")
        return

    table = Table(title="Available Workflows", title_style="bold cyan")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="white bold")
    table.add_column("Steps", style="magenta", justify="center")
    table.add_column("Inputs", style="green")
    table.add_column("Description", style="dim")

    for wf_id, wf in workflows.items():
        input_names = [f["name"] for f in wf.get("inputs", [])]
        table.add_row(
            wf_id,
            wf.get("name", wf_id),
            str(wf.get("step_count", 0)),
            ", ".join(input_names) if input_names else "none",
            wf.get("description", "")
        )

    console.print(table)


@app.command("run")
def run_workflow(
    workflow_name: str = typer.Argument(..., help="Workflow ID to execute"),
    set_params: Optional[List[str]] = typer.Option(
        None, "--set", "-s", help="Set input parameters in key=value format"
    ),
    output_format: str = typer.Option("rich", "--output", "-o", help="Output format: 'rich' or 'json'"),
    interactive: bool = typer.Option(True, "--interactive/--non-interactive", help="Prompt for missing required inputs"),
    env: str = typer.Option("dev", "--env", "-e", help="Environment partition ('dev', 'uat', 'prod')")
):
    """Execute a workflow directly in the terminal."""
    registry.discover()
    wf_class = registry.get(workflow_name)
    if not wf_class:
        console.print(f"[red]Error: Workflow '{workflow_name}' not found.[/red]")
        console.print(f"Available: {list(registry.list_workflows().keys())}")
        raise typer.Exit(code=1)

    wf_instance = wf_class()
    inputs = {}

    # 1. Parse --set arguments
    if set_params:
        for item in set_params:
            if "=" in item:
                k, v = item.split("=", 1)
                inputs[k.strip()] = v.strip()

    # 2. Check required inputs (Prompt ONLY if required and no default exists)
    for field in wf_instance.inputs():
        if field.name not in inputs:
            if field.required and field.default is None:
                if interactive:
                    if field.sensitive:
                        val = getpass.getpass(f"Enter {field.label or field.name} (secret): ")
                    else:
                        val = typer.prompt(f"Enter {field.label or field.name}")
                    inputs[field.name] = val
                else:
                    console.print(f"[red]Missing required input: {field.name}[/red]")
                    raise typer.Exit(code=1)
            elif field.default is not None:
                inputs[field.name] = field.default

    runner = WorkflowRunner(workflow=wf_instance, environment=env)

    if output_format != "json":
        console.print(Panel(f"[bold cyan]Running Workflow:[/] [bold white]{wf_instance.name}[/] ([dim]{runner.run_id}[/]) [dim][{env.upper()}][/dim]"))

    result = asyncio.run(runner.run(inputs))

    # Save to SQLite database
    save_run_result(result, inputs, env=env)

    if output_format == "json":
        print(json.dumps(result.model_dump(), indent=2))
    else:
        # Render step table
        table = Table(title="Workflow Execution Summary", title_style="bold green" if result.success else "bold red")
        table.add_column("Step", style="white bold")
        table.add_column("Status", justify="center")
        table.add_column("Time", justify="right")
        table.add_column("Message", style="dim")
        table.add_column("Metrics", style="cyan")

        for s in result.results:
            status_badge = (
                "[green]✓ SUCCESS[/green]" if s.status == StepStatus.SUCCESS
                else "[red]✗ FAILED[/red]" if s.status == StepStatus.FAILED
                else "[yellow]↷ SKIPPED[/yellow]"
            )
            metrics_str = ", ".join(f"{k}={v}" for k, v in s.metrics.items()) if s.metrics else "-"
            table.add_row(
                s.name,
                status_badge,
                f"{s.time_taken:.2f}s" if s.executed else "-",
                s.message,
                metrics_str
            )

        console.print(table)
        duration_color = "green" if result.success else "red"
        console.print(
            f"[{duration_color}]Result: {'SUCCESS' if result.success else 'FAILED'} | "
            f"Steps: {result.successful_steps}/{result.total_steps} passed | "
            f"Total time: {result.total_time:.2f}s | "
            f"Run ID: {result.run_id}[/{duration_color}]\n"
        )

    if not result.success:
        raise typer.Exit(code=1)


@app.command("runs")
def show_run_history(
    limit: int = typer.Option(15, "--limit", "-n", help="Number of runs to display"),
    workflow: Optional[str] = typer.Option(None, "--workflow", "-w", help="Filter by workflow name")
):
    """View recent execution history from the local database."""
    runs = get_recent_runs(limit=limit, workflow_name=workflow)
    if not runs:
        console.print("[yellow]No execution history recorded yet.[/yellow]")
        return

    table = Table(title="Recent Workflow Executions", title_style="bold blue")
    table.add_column("Run ID", style="cyan")
    table.add_column("Workflow", style="white bold")
    table.add_column("Status", justify="center")
    table.add_column("Steps", justify="center")
    table.add_column("Duration", justify="right")
    table.add_column("Started At", style="dim")

    for r in runs:
        status_style = "green" if r["status"] == "completed" and r["success"] else "red" if r["status"] == "failed" else "yellow"
        table.add_row(
            r["id"],
            r["workflow_name"],
            f"[{status_style}]{r['status'].upper()}[/{status_style}]",
            f"{r['successful_steps']}/{r['total_steps']}",
            f"{r['total_time']:.2f}s",
            r["started_at"].split("T")[0] + " " + r["started_at"].split("T")[1][:8]
        )

    console.print(table)


@app.command("serve")
def start_server(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Port number"),
    reload: bool = typer.Option(False, "--reload", help="Enable hot reload")
):
    """Launch the Valiant FastAPI service and Web UI."""
    import uvicorn
    console.print(Panel(
        f"[bold green]Starting Valiant Platform[/]\n"
        f"API & Swagger: [cyan]http://{host}:{port}/docs[/]\n"
        f"Web Dashboard: [cyan]http://{host}:{port}/[/]",
        title="Valiant Server"
    ))
    uvicorn.run("backend.valiant.api.app:app", host=host, port=port, reload=reload)


@app.command("new")
def scaffold_workflow(
    name: str = typer.Argument(..., help="Workflow name in snake_case (e.g. data_sync)"),
    directory: str = typer.Option("backend/workflows", "--dir", "-d", help="Target directory"),
    style: str = typer.Option("compact", "--style", "-s", help="Template style: 'compact' (modern type-annotated), 'functional' (micro-workflow), or 'standard'")
):
    """Scaffold a new production-ready workflow template file."""
    class_name = "".join(part.capitalize() for part in name.split("_")) + "Workflow"
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{name}.py"

    if target_file.exists():
        console.print(f"[red]Error: File {target_file} already exists.[/red]")
        raise typer.Exit(code=1)

    if style.lower() == "functional":
        template_code = f'''\"\"\"
{name} - Functional Micro-Workflow
\"\"\"
from backend.valiant import workflow

wf = workflow(
    "{name}",
    description="Functional workflow for {name.replace('_', ' ')}",
    tags=["micro", "automation"]
)

# Declare parameters (or let them auto-infer from step arguments)
wf.input("job_name", type=str, default="{name}_run", help_text="Job identifier")
wf.input("batch_size", type=int, default=100)
wf.input("notify", type=bool, default=True)

@wf.step("Validate Inputs")
def validate_inputs(job_name: str = "{name}_run", batch_size: int = 100):
    # Parameters are auto-injected from workflow inputs!
    return f"Validated {{job_name}} for {{batch_size}} records"

@wf.approval("Operator Sign-off", prompt="Authorize execution to proceed?")
def operator_signoff():
    pass

@wf.step("Process Data")
async def process_data(ctx, batch_size: int = 100):
    ctx.log(f"Processing batch of {{batch_size}} records in real-time")
    ctx["processed_count"] = batch_size
    return {{"status": "ok", "processed": batch_size}}

@wf.step("Send Notification", condition="notify")
def send_notification(ctx):
    count = ctx.get("processed_count", 0)
    return f"Notification dispatched for {{count}} items"
'''
    elif style.lower() == "compact":
        template_code = f'''\"\"\"
{class_name} - Modern Compact Workflow
\"\"\"
from typing import Literal
from backend.valiant import Workflow, step, workflow


@workflow(name="{name}", description="Automated workflow for {name.replace('_', ' ')}")
class {class_name}(Workflow):
    name = "{name.replace('_', ' ').title()}"
    tags = ["automation", "compact"]

    # Typed parameters auto-generate UI forms and API schemas (zero InputField ceremony)
    job_name: str = "{name}_run"
    batch_size: int = 100
    notify: bool = True
    mode: Literal["fast", "standard", "thorough"] = "standard"

    @step("Validate Inputs")
    def validate_inputs(self, job_name: str, batch_size: int):
        # Parameters are auto-injected from context/inputs!
        return f"Validated {{job_name}} with batch size {{batch_size}}"

    @step("Process Data")
    async def process_data(self, ctx, batch_size: int):
        ctx["processed_count"] = batch_size
        return {{"status": "ok", "processed": batch_size}}

    @step("Send Notification", condition="notify")
    def send_notification(self, ctx):
        count = ctx.get("processed_count", 0)
        return f"Notification sent for {{count}} items"
'''
    else:
        template_code = f'''\"\"\"
{class_name} - Automated Workflow
\"\"\"
from backend.valiant import Workflow, step, workflow, InputField, InputType


@workflow(name="{name}", description="Automated workflow for {name.replace('_', ' ')}")
class {class_name}(Workflow):
    name = "{name.replace('_', ' ').title()}"
    description = "Generated workflow"
    version = "1.0.0"
    tags = ["custom", "automation"]

    def inputs(self):
        return [
            InputField("job_name", type=InputType.TEXT, required=True, default="{name}_run", help_text="Job identifier"),
            InputField("batch_size", type=InputType.NUMBER, default=100, min_value=1, max_value=10000),
            InputField("notify", type=InputType.CHECKBOX, default=True, help_text="Send completion notification")
        ]

    @step("Validate Inputs", order=1, tags=["validation"])
    def validate_inputs(self, context):
        job_name = context.get("job_name")
        res = self.success(f"Parameters validated for {{job_name}}")
        res.add_metric("batch_size", context.get("batch_size"))
        return res

    @step("Process Data", order=2, tags=["processing"])
    def process_data(self, context):
        batch_size = context.get("batch_size", 100)
        context["processed_count"] = batch_size
        return self.success(f"Processed {{batch_size}} records successfully")

    @step("Send Notification", order=3, condition="notify", tags=["notification"])
    def send_notification(self, context):
        count = context.get("processed_count", 0)
        return self.success(f"Notification sent for {{count}} processed items")
'''

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(template_code)

    console.print(f"[bold green]✓ Created new {style} workflow:[/] [cyan]{target_file}[/]")

    console.print(f"Run it now: [white]python run.py run {name}[/]")


@app.command("report")
def generate_report_cmd(
    run_id: str = typer.Argument(..., help="Run ID to generate HTML report for"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Target output file path (.html)"),
    env: str = typer.Option("dev", "--env", "-e", help="Environment partition ('dev', 'uat', 'prod')"),
    open_browser: bool = typer.Option(False, "--open", help="Open report in default web browser immediately")
):
    """Generate self-contained standalone HTML report for a workflow run."""
    import webbrowser
    from ..db.database import get_run_by_id
    from ..core.environments import normalize_environment
    from ..core.report import generate_run_html_report

    target_env = normalize_environment(env)
    run_data = get_run_by_id(run_id, env=target_env)
    if not run_data:
        console.print(f"[red]Error: Run '{run_id}' not found in [{target_env.upper()}] environment.[/red]")
        raise typer.Exit(code=1)

    html_content = generate_run_html_report(run_data, env=target_env)
    out_path = Path(output) if output else Path(f"valiant_report_{run_id}_{target_env}.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")

    console.print(f"[bold green]✓ Report generated successfully:[/] [cyan]{out_path.resolve()}[/]")
    if open_browser:
        webbrowser.open(out_path.resolve().as_uri())


@app.command("logs")
def view_run_logs_cmd(
    run_id: str = typer.Argument(..., help="Run ID to inspect logs for"),
    env: str = typer.Option("dev", "--env", "-e", help="Environment partition ('dev', 'uat', 'prod')"),
    tail: Optional[int] = typer.Option(None, "--tail", "-n", help="Display only the last N lines"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Continuously output appended log lines")
):
    """View or follow raw execution log file for a specific workflow run."""
    import time
    from ..core.environments import normalize_environment
    from ..core.logging import RunLogManager

    target_env = normalize_environment(env)
    log_path = RunLogManager.get_path(run_id, env=target_env)

    if not log_path.exists():
        console.print(f"[yellow]Log file not found at: {log_path.resolve()}[/yellow]")
        console.print(f"[dim]Checking SQLite database for execution logs...[/dim]")
        from ..db.database import get_run_by_id
        run_data = get_run_by_id(run_id, env=target_env)
        if not run_data:
            console.print(f"[red]Error: Run '{run_id}' not found in [{target_env.upper()}] environment.[/red]")
            raise typer.Exit(code=1)
        console.print(RunLogManager.read_log_content(run_id, env=target_env))
        return

    if not follow:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        if tail and tail > 0:
            lines = lines[-tail:]
        for line in lines:
            console.print(line)
        return

    # Follow mode (tail -f)
    console.print(f"[cyan]Streaming live logs for {run_id} ({log_path.resolve()}) [Ctrl+C to stop]...[/cyan]\n")
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        if tail and tail > 0:
            lines = f.readlines()
            for line in lines[-tail:]:
                console.print(line.rstrip())
        else:
            f.seek(0, os.SEEK_END)

        try:
            while True:
                line = f.readline()
                if line:
                    console.print(line.rstrip())
                else:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped log streaming.[/dim]")


def main():
    app()


if __name__ == "__main__":
    main()
