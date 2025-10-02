import typer
import importlib
import asyncio
import sys
import getpass
import os
from typing import List, Optional, Tuple, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
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
        
        # Check if it's the new unified workflow or legacy
        from valiant.framework.workflow_unified import Workflow
        from valiant.framework.workflow import BaseWorkflow
        
        if not (issubclass(workflow_class, Workflow) or issubclass(workflow_class, BaseWorkflow)):
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
                "attempts": r.attempts,
                "derived_metrics": getattr(r, 'derived_metrics', {}),
                "tags": getattr(r, 'tags', [])
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
        set_context: Optional[List[str]] = typer.Option(
            None,
            "--set",
            help="Set manual context values (key=value format, can be used multiple times)"
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
        for item in set_context:
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
def create(
        template_name: Optional[str] = typer.Argument(None, help="Template name (api_db_integration)"),
        output_dir: str = typer.Option("./", "--output", "-o", help="Output directory for generated files"),
        interactive: bool = typer.Option(True, "--interactive/--non-interactive", help="Interactive mode")
):
    """Create a new workflow from a template"""
    from valiant.templates import TemplateEngine
    
    engine = TemplateEngine()
    available_templates = engine.list_templates()
    
    if not available_templates:
        console.print("[red]No templates available[/]")
        raise typer.Exit(1)
    
    # Show available templates if none specified
    if not template_name:
        console.print("[bold]Available Templates:[/]")
        table = Table(title="Workflow Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Category", style="dim")
        
        for template in available_templates:
            table.add_row(template.name, template.description, template.category)
        
        console.print(table)
        
        if interactive:
            template_name = Prompt.ask("\nWhich template would you like to use?", 
                                     choices=[t.name for t in available_templates])
        else:
            console.print(f"\n[yellow]Please specify a template name. Available: {[t.name for t in available_templates]}[/]")
            raise typer.Exit(1)
    
    # Validate template exists
    if template_name not in [t.name for t in available_templates]:
        console.print(f"[red]Template '{template_name}' not found[/]")
        console.print(f"[yellow]Available: {[t.name for t in available_templates]}[/]")
        raise typer.Exit(1)
    
    # Create output directory if it doesn't exist
    output_path = os.path.abspath(output_dir)
    os.makedirs(output_path, exist_ok=True)
    
    try:
        # Generate workflow
        console.print(f"\n[bold green]Creating workflow from template: {template_name}[/]")
        
        if interactive:
            console.print("[dim]Answer the following questions to configure your workflow:[/]")
        
        generated_files = engine.generate_workflow(template_name, output_path, interactive=interactive)
        
        # Display results
        console.print(f"\n[bold green]✓ Successfully generated {len(generated_files)} files:[/]")
        
        for file in generated_files:
            file_path = os.path.join(output_path, file.path)
            console.print(f"  [cyan]{file.file_type.upper()}[/]: {file_path}")
        
        # Show next steps
        console.print(f"\n[bold]Next Steps:[/]")
        console.print("1. Review the generated files")
        console.print("2. Customize the workflow logic as needed")
        console.print("3. Test the workflow:")
        
        workflow_files = [f for f in generated_files if f.file_type == "workflow"]
        if workflow_files:
            workflow_file = workflow_files[0]
            workflow_name = workflow_file.path.replace('.py', '')
            console.print(f"   [dim]python run.py run {workflow_name}[/]")
        
        console.print("4. Register in valiant/workflows/config.py if needed")
        
    except Exception as e:
        console.print(f"[red]Error generating workflow: {e}[/]")
        raise typer.Exit(1)


@app.command()
def list(
        output_format: str = typer.Option("rich", "--output", help="Output format: rich or json")
):
    """List all available workflows"""
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