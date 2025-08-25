import typer
import importlib
import asyncio
import sys
import getpass
from typing import List, Optional, Tuple, Dict, Any
from rich.console import Console
from valiant.framework.engine import WorkflowRunner, print_summary, StepResult
from valiant.framework.workflow import BaseWorkflow
from valiant.framework.registry import get_available_workflows, get_workflow_class_path

app = typer.Typer()
console = Console()


def load_workflow(workflow_identifier: str) -> type:
    """Load a workflow class by short name or full path"""
    # First check if it's a registered short name
    full_path = get_workflow_class_path(workflow_identifier)

    # If not found in registry, treat as full path
    if full_path is None:
        full_path = workflow_identifier

    try:
        module_name, class_name = full_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        workflow_class = getattr(module, class_name)
        if not issubclass(workflow_class, BaseWorkflow):
            raise TypeError("Not a valid workflow class")
        return workflow_class
    except (ImportError, AttributeError, ValueError, TypeError) as e:
        console.print(f"[red]Error loading workflow: {e}[/]")
        console.print(f"[yellow]Available workflows: {list(get_available_workflows().keys())}[/]")
        raise typer.Exit(1)


def print_json_summary(results: List[StepResult]) -> str:
    """Return results as JSON string"""
    import json
    summary_data = {
        "steps": [
            {
                "name": r.name,
                "success": r.success,
                "message": r.message,
                "skipped": r.skipped,
                "executed": r.executed,
                "time_taken": round(r.time_taken, 2),
                "attempts": r.attempts
            }
            for r in results
        ],
        "summary": {
            "total_steps": len(results),
            "executed_steps": sum(1 for r in results if r.executed),
            "successful_steps": sum(1 for r in results if r.success and r.executed),
            "skipped_steps": sum(1 for r in results if r.skipped),
            "total_time": round(sum(r.time_taken for r in results if r.executed), 2)
        }
    }
    return json.dumps(summary_data, indent=2)


@app.command()
def run(
        workflow: str = typer.Argument(..., help="Workflow name or full class path"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
        timeout: float = typer.Option(30.0, help="Default timeout per step in seconds"),
        retries: int = typer.Option(1, help="Number of retries for failed steps"),
        output_format: str = typer.Option("rich", "--output", help="Output format: rich or json"),
        save_context: bool = typer.Option(False, help="Save context to context.json"),
        set_context: Optional[str] = typer.Option(
            None,
            "--set",
            help="Set manual context values (comma-separated key=value pairs)"
        ),
        environment: str = typer.Option(
            None,
            "--env",
            help="Environment to load configuration for (dev, prod, test)"
        ),
        config_dir: str = typer.Option(
            "config",
            "--config-dir",
            help="Configuration directory path"
        )
):
    """Run a validation workflow"""
    # Load workflow class
    workflow_class = load_workflow(workflow)

    # Initialize runner
    runner = WorkflowRunner(
        verbose=verbose,
        timeout=timeout,
        max_retries=retries,
        output_format=output_format,
        environment=environment,
        config_dir=config_dir
    )

    # Create workflow instance
    workflow_instance = workflow_class(runner)

    # Set manual context values
    if set_context:
        for item in set_context.split(','):
            if '=' in item:
                key, value = item.split('=', 1)
                runner.context[key] = value
                if output_format != "json":
                    console.print(f"[dim]Set context: {key} = {value}[/]")

    # Get required inputs using the new system
    for prompt, key, is_secret in workflow_instance.get_required_inputs():
        if key not in runner.context:
            value = runner.get_input(prompt, key, is_secret)
            runner.context[key] = value

    # Setup workflow
    workflow_instance.setup()

    # Define steps
    workflow_instance.define_steps()

    # Run workflow
    asyncio.run(runner.run())

    # Print summary
    if output_format != "json":
        console.rule("[bold blue]Workflow Complete[/]")

    if output_format == "json":
        print(print_json_summary(runner.results))
    else:
        print_summary(runner.results, verbose, output_format)

    # Save context if requested
    if save_context:
        runner.save_context()

    # Exit code based on success
    if any(result.executed and not result.success for result in runner.results):
        raise typer.Exit(code=1)


@app.command()
def list(
        output_format: str = typer.Option("rich", "--output", help="Output format: rich or json")
):
    """List all available workflows"""
    from rich.table import Table
    workflows = get_available_workflows()

    if output_format == "json":
        import json
        print(json.dumps(workflows, indent=2))
        return

    if not workflows:
        console.print("[yellow]No workflows found.[/]")
        return

    table = Table(title="Available Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Class Path", style="dim")

    for name, class_path in workflows.items():
        table.add_row(name, class_path)

    console.print(table)


def get_config_value(key: str, prompt: str, hide_input: bool = False) -> str:
    """Get value from environment or prompt user"""
    import os
    value = os.getenv(key)
    if value:
        return value

    if hide_input:
        return getpass.getpass(prompt)
    else:
        return input(prompt)


if __name__ == "__main__":
    app()