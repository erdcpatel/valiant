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

app = typer.Typer(
    name="valiant",
    help="ValiantFlow — Developer-First Python Workflow Automation & Orchestration Platform",
    no_args_is_help=True,
    rich_markup_mode="rich"
)
console = Console()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Display ValiantFlow version")
):
    """ValiantFlow — Developer-First Python Workflow Automation & Orchestration Platform."""
    from .. import __version__
    if version:
        console.print(f"[bold cyan]ValiantFlow Platform CLI[/] v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(Panel(
            f"[bold cyan]ValiantFlow[/] [dim]v{__version__}[/dim] — Enterprise Python Workflow Automation & Orchestration\n\n"
            f"[bold white]Core Commands:[reset]\n"
            f"  [cyan]valiant list[/]                     List all discovered workflows in current workspace\n"
            f"  [cyan]valiant run <id>[/reset]                 Execute a workflow directly in the terminal\n"
            f"  [cyan]valiant serve[/reset]                    Launch Web Dashboard & REST API with smart port selection\n"
            f"  [cyan]valiant init[/reset]                     Initialize a project directory with workflows/ and starter template\n"
            f"  [cyan]valiant new <name>[/reset]               Scaffold a new production-ready workflow template\n"
            f"  [cyan]valiant runs[/reset]                     Query and inspect persistent run execution history\n"
            f"  [cyan]valiant report <run_id>[/reset]          Generate interactive offline-ready multi-tab HTML report\n"
            f"  [cyan]valiant logs <run_id>[/reset]            Stream or tail dedicated per-run raw execution logs\n\n"
            f"[bold white]Getting Started:[reset]\n"
            f"  [dim]$[/] [white]valiant init[/]                  [dim]# Set up workflows/ directory[/dim]\n"
            f"  [dim]$[/] [white]valiant run starter_workflow[/]  [dim]# Run starter workflow in DEV[/dim]\n"
            f"  [dim]$[/] [white]valiant serve[/]                 [dim]# Open dashboard at http://localhost:8000[/dim]\n\n"
            f"[dim]Run [bold white]valiant <command> --help[/bold white] for detailed options on any command.[/dim]",
            title="[bold cyan]⚡ ValiantFlow CLI[/]",
            border_style="cyan"
        ))
        raise typer.Exit()



@app.command("list")
def list_workflows(
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Directory or file containing workflows"),
    include_defaults: bool = typer.Option(True, "--defaults/--no-defaults", help="Include built-in template workflows")
):
    """List all available workflows."""
    search_dirs = [directory] if directory else None
    registry.discover(search_dirs=search_dirs)
    hide_env = os.environ.get("VALIANT_HIDE_DEFAULTS", "0").lower() in ("1", "true", "yes")
    effective_include = include_defaults and not hide_env
    workflows = registry.list_workflows(include_defaults=effective_include)

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
    env: str = typer.Option("dev", "--env", "-e", help="Environment partition ('dev', 'uat', 'prod')"),
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Directory or file containing workflows")
):
    """Execute a workflow directly in the terminal."""
    search_dirs = [directory] if directory else None
    registry.discover(search_dirs=search_dirs)
    wf_instance = registry.get_instance(workflow_name)
    if not wf_instance:
        console.print(f"[red]Error: Workflow '{workflow_name}' not found.[/red]")
        console.print(f"Available: {list(registry.list_workflows().keys())}")
        raise typer.Exit(code=1)

    inputs = {}

    # 1. Parse --set arguments
    if set_params:
        for item in set_params:
            if "=" in item:
                k, v = item.split("=", 1)
                inputs[k.strip()] = v.strip()
            else:
                console.print(f"[yellow]Warning: Ignoring malformed --set argument '{item}' (expected key=value)[/yellow]")

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
    workflow: Optional[str] = typer.Option(None, "--workflow", "-w", help="Filter by workflow name"),
    env: str = typer.Option("dev", "--env", "-e", help="Environment partition ('dev', 'uat', 'prod')")
):
    """View recent execution history from the local database."""
    from ..core.environments import normalize_environment
    target_env = normalize_environment(env)
    runs = get_recent_runs(limit=limit, workflow_name=workflow, env=target_env)
    if not runs:
        console.print(f"[yellow]No execution history recorded yet in [{target_env.upper()}].[/yellow]")
        return

    table = Table(title=f"Recent Workflow Executions [{target_env.upper()}]", title_style="bold blue")
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


def _is_port_available(host: str, port: int) -> bool:
    """Check if a TCP port is available for binding."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # On 0.0.0.0 bind, check 127.0.0.1 and 0.0.0.0
            test_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
            s.bind((test_host, port))
            return True
        except OSError:
            return False


def _find_available_port(host: str, start_port: int, max_attempts: int = 50) -> int:
    """Find the next available port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if _is_port_available(host, p):
            return p
    return start_port


@app.command("serve")
def start_server(
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Bind host (or VALIANT_HOST env)"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port number (or VALIANT_PORT / PORT env)"),
    strict_port: bool = typer.Option(False, "--strict-port", help="Do not attempt to auto-select next available port if busy"),
    reload: bool = typer.Option(False, "--reload", help="Enable hot reload"),
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Directory or file containing workflows")
):
    """Launch the Valiant FastAPI service and Web UI with smart port resolution."""
    if directory:
        os.environ["VALIANT_WORKFLOWS_DIR"] = str(Path(directory).resolve())

    # Resolve host from arg or env
    effective_host = host or os.environ.get("VALIANT_HOST") or "0.0.0.0"

    # Resolve port from arg or env (VALIANT_PORT or PORT)
    env_port = os.environ.get("VALIANT_PORT") or os.environ.get("PORT")
    desired_port = port if port is not None else (int(env_port) if env_port and env_port.isdigit() else 8000)

    # Check port availability
    chosen_port = desired_port
    if not _is_port_available(effective_host, desired_port):
        if strict_port:
            console.print(f"[bold red]Error: Port {desired_port} is already in use and --strict-port was specified.[/]")
            raise typer.Exit(code=1)
        available = _find_available_port(effective_host, desired_port + 1)
        console.print(
            f"[yellow]Notice: Desired port {desired_port} is in use. Auto-selected next free port: [bold cyan]{available}[/bold cyan][/yellow]"
        )
        chosen_port = available

    display_host = "127.0.0.1" if effective_host == "0.0.0.0" else effective_host
    import uvicorn
    console.print(Panel(
        f"[bold green]Starting Valiant Platform[/]\n\n"
        f"  Web Dashboard:  [bold cyan]http://{display_host}:{chosen_port}/[/]\n"
        f"  REST API & Docs: [cyan]http://{display_host}:{chosen_port}/docs[/]\n"
        f"  Bound Address:  [dim]{effective_host}:{chosen_port}[/dim]",
        title="Valiant Server"
    ))
    uvicorn.run("backend.valiant.api.app:app", host=effective_host, port=chosen_port, reload=reload)


@app.command("new")
def scaffold_workflow(
    name: str = typer.Argument(..., help="Workflow name in snake_case (e.g. data_sync)"),
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Target directory (defaults to 'workflows' or 'backend/workflows')"),
    style: str = typer.Option("compact", "--style", "-s", help="Template style: 'compact' (modern type-annotated), 'functional' (micro-workflow), or 'standard'")
):
    """Scaffold a new production-ready workflow template file."""
    import re
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_").lower()
    if clean_name and clean_name[0].isdigit():
        clean_name = f"wf_{clean_name}"
    if clean_name != name:
        console.print(f"[yellow]Notice: Normalizing workflow name '{name}' to valid Python identifier '{clean_name}'[/yellow]")
        name = clean_name

    class_name = "".join(part.capitalize() for part in name.split("_")) + "Workflow"
    if directory:
        target_dir = Path(directory)
    elif Path("backend/workflows").is_dir():
        target_dir = Path("backend/workflows")
    else:
        target_dir = Path("workflows")

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{name}.py"

    if target_file.exists():
        console.print(f"[red]Error: File {target_file} already exists.[/red]")
        raise typer.Exit(code=1)

    if style.lower() == "functional":
        template_code = f'''\"\"\"
{name} - Functional Micro-Workflow
\"\"\"
from valiantflow import workflow

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
from valiantflow import Workflow, step, workflow


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
from valiantflow import Workflow, step, workflow, InputField, InputType


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

    console.print(f"Run it now: [white]valiant run {name}[/]")


@app.command("init")
def init_project(
    directory: str = typer.Option(".", "--dir", "-d", help="Target project root directory (defaults to current directory)"),
    style: str = typer.Option("compact", "--style", "-s", help="Workflow template style: 'compact' or 'functional'")
):
    """Initialize a new Valiant workflow project with starter template and folder structure."""
    target_root = Path(directory).resolve()
    workflows_dir = target_root / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    starter_file = workflows_dir / "starter_workflow.py"
    if not starter_file.exists():
        if style.lower() == "functional":
            starter_content = '''\"\"\"
Starter Workflow - Functional Micro-Workflow
\"\"\"
from valiantflow import workflow

wf = workflow(
    "starter_workflow",
    description="A starter workflow demonstrating parameters and steps",
    tags=["starter", "demo"]
)

wf.input("greeting_target", type=str, default="World", help_text="Target of the greeting")
wf.input("iterations", type=int, default=3, help_text="Number of iterations to process")

@wf.step("Validate Setup")
def validate_setup(greeting_target: str = "World", iterations: int = 3):
    return f"Ready to greet {greeting_target} {iterations} times"

@wf.step("Process Items")
async def process_items(ctx, greeting_target: str = "World", iterations: int = 3):
    results = []
    for i in range(1, iterations + 1):
        msg = f"Hello {greeting_target}! (#{i})"
        ctx.log(msg)
        results.append(msg)
    ctx["items"] = results
    return {"status": "success", "count": len(results)}

@wf.step("Final Summary")
def final_summary(ctx):
    count = len(ctx.get("items", []))
    return f"Completed greeting sequence for {count} messages"
'''
        else:
            starter_content = '''\"\"\"
Starter Workflow - Modern Compact Style
\"\"\"
from typing import Literal
from valiantflow import Workflow, step, workflow


@workflow(name="starter_workflow", description="A starter workflow demonstrating parameters and steps")
class StarterWorkflow(Workflow):
    name = "Starter Workflow"
    tags = ["starter", "demo"]

    # Parameter declarations (auto-inferred inputs and UI schema)
    greeting_target: str = "World"
    iterations: int = 3
    mode: Literal["fast", "thorough"] = "fast"

    @step("Validate Setup")
    def validate_setup(self, greeting_target: str, iterations: int):
        return f"Ready to greet {greeting_target} {iterations} times"

    @step("Process Items")
    async def process_items(self, ctx, greeting_target: str, iterations: int):
        results = []
        for i in range(1, iterations + 1):
            msg = f"Hello {greeting_target}! (#{i})"
            ctx.log(msg)
            results.append(msg)
        ctx["items"] = results
        return {"status": "success", "count": len(results)}

    @step("Final Summary")
    def final_summary(self, ctx):
        count = len(ctx.get("items", []))
        return f"Completed greeting sequence for {count} messages"
'''
        starter_file.write_text(starter_content, encoding="utf-8")

    # Also create a .env template if not present
    env_file = target_root / ".env"
    if not env_file.exists():
        env_content = """# ValiantFlow Environment Configuration
VALIANT_ENV=dev
VALIANT_WORKFLOWS_DIR=./workflows
"""
        env_file.write_text(env_content, encoding="utf-8")

    console.print(Panel(
        f"[bold green]✓ ValiantFlow project initialized successfully![/]\n\n"
        f"  Workflows folder:  [cyan]{workflows_dir}[/]\n"
        f"  Starter workflow:  [cyan]{starter_file}[/]\n\n"
        f"[bold white]Next Steps:[reset]\n"
        f"  1. [white]valiant list[/]                      (list available workflows)\n"
        f"  2. [white]valiant run starter_workflow[/]      (run the starter workflow)\n"
        f"  3. [white]valiant serve[/]                     (launch web dashboard at http://localhost:8000)\n"
        f"  4. [white]valiant new my_flow[/]               (scaffold a new custom workflow)",
        title="ValiantFlow Project Setup"
    ))


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
