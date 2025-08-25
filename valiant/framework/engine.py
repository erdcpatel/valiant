import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Dict, Callable, List, Tuple, Optional, Union, Awaitable
from rich.console import Console
from rich.table import Table
import os
from dotenv import load_dotenv
import inspect
import json
import traceback
import getpass

# Add this import
from valiant.framework.config_loader import ConfigLoader

console = Console()
load_dotenv()


class StepResult:
    def __init__(self, name: str):
        self.name = name
        self.success: bool = False
        self.message: str = ""
        self.skipped: bool = False
        self.executed: bool = False
        self.time_taken: float = 0.0
        self.attempts: int = 1
        self.exception: Optional[Exception] = None
        self.data: object = None


# Define a type alias for better readability
StepFunction = Union[
    Callable[[Dict], Tuple[bool, str, object]],
    Callable[[Dict], Awaitable[Tuple[bool, str, object]]]
]


class WorkflowRunner:
    def __init__(self,
                 stop_on_failure: bool = True,
                 verbose: bool = False,
                 timeout: float = 30.0,
                 max_retries: int = 1,
                 output_format: str = "rich",
                 environment: str = None,
                 config_dir: str = "config"
                 ):
        self.context: Dict = {}
        self.stop_on_failure = stop_on_failure
        self.verbose = verbose
        self.timeout = timeout
        self.max_retries = max_retries
        self.output_format = output_format
        self.steps: List[Dict] = []
        self.results: List[StepResult] = []
        self.thread_pool = ThreadPoolExecutor()

        # Load configurations
        config_loader = ConfigLoader(config_dir)
        config = config_loader.load_configurations(environment)
        self.context.update(config)

    def add_step(
            self,
            name: str,
            func: StepFunction,
            requires: Optional[List[str]] = None,
            parallel_group: Optional[str] = None,
            timeout: Optional[float] = None,
            retries: Optional[int] = None
    ):
        """Add a step to the workflow."""
        step_timeout = timeout if timeout is not None else self.timeout
        step_retries = retries if retries is not None else self.max_retries

        self.steps.append({
            "name": name,
            "func": func,
            "requires": requires or [],
            "parallel_group": parallel_group,
            "timeout": step_timeout,
            "retries": step_retries
        })


    async def run_step(self, step: Dict) -> StepResult:
        """Execute a single step with retries and timeout."""
        result = StepResult(step["name"])
        timeout = step["timeout"]
        max_retries = step["retries"]

        # Check dependencies
        missing_deps = [dep for dep in step["requires"] if dep not in self.context]
        if missing_deps:
            result.skipped = True
            result.message = f"Missing dependencies: {', '.join(missing_deps)}"
            return result

        # Check if we should stop due to previous failure
        if self.stop_on_failure and any(not r.success and not r.skipped for r in self.results):
            result.skipped = True
            result.message = "Skipped due to previous failure"
            return result

        # Execute the step with retries
        start_time = time.time()
        result.executed = True

        for attempt in range(1, max_retries + 2):  # +1 for initial attempt
            try:
                func = step["func"]
                if inspect.iscoroutinefunction(func):
                    success, message, data = await asyncio.wait_for(
                        func(self.context),
                        timeout=timeout
                    )
                else:
                    loop = asyncio.get_running_loop()
                    success, message, data = await asyncio.wait_for(
                        loop.run_in_executor(self.thread_pool, func, self.context),
                        timeout=timeout
                    )

                result.success = success
                result.message = message
                result.data = data
                result.attempts = attempt
                break
            except asyncio.TimeoutError:
                result.message = f"Timeout after {timeout} seconds"
                if attempt > max_retries:
                    result.success = False
                    if self.verbose:
                        result.message += f" (attempt {attempt}/{max_retries + 1})"
                    break
            except Exception as e:
                result.exception = e
                if attempt > max_retries:
                    result.success = False
                    result.message = f"Error: {str(e)}"
                    if self.verbose:
                        result.message += f"\n{traceback.format_exc()}"
                    break
                elif self.verbose:
                    console.print(f"[yellow]Attempt {attempt} failed: {str(e)}[/]")
            finally:
                result.time_taken = time.time() - start_time

        return result

    async def run(self):
        """Execute the workflow with parallel group support."""
        # Group steps by parallel_group
        groups = {}
        for step in self.steps:
            group_key = step["parallel_group"] or step["name"]
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(step)

        # Process groups sequentially, steps within groups in parallel
        for group_key, group_steps in groups.items():
            # Skip group if previous failure and stop_on_failure enabled
            if self.stop_on_failure and any(not r.success and not r.skipped for r in self.results):
                for step in group_steps:
                    result = StepResult(step["name"])
                    result.skipped = True
                    result.message = "Skipped due to previous failure"
                    self.results.append(result)
                    if self.output_format != "json":
                        console.print(f"{step['name']}: [yellow]↷ Skipped[/]")
                continue

            # Execute steps in parallel
            tasks = [self.run_step(step) for step in group_steps]
            group_results = await asyncio.gather(*tasks)

            for result in group_results:
                self.results.append(result)
                if self.output_format == "json":
                    continue

                if result.skipped:
                    console.print(f"{result.name}: [yellow]↷ Skipped[/]")
                elif result.success:
                    console.print(f"{result.name}: [green]✓ Success[/] (took {result.time_taken:.2f}s)")
                else:
                    # Truncate long error messages
                    error_msg = result.message
                    if len(error_msg) > 200 and not self.verbose:
                        error_msg = error_msg[:200] + "... [truncated]"

                    console.print(f"{result.name}: [red]✗ Failed[/] (took {result.time_taken:.2f}s)")
                    console.print(f"   → {error_msg}", style="red")

    def save_context(self, filename: str = "context.json"):
        """Save workflow context to a file for debugging."""
        with open(filename, "w") as f:
            json.dump(self.context, f, indent=2)
        if self.output_format != "json":
            console.print(f"[dim]Context saved to {filename}[/]")

    def get_input(self, prompt: str, key: str, is_secret: bool = False) -> str:
        """Prompt user for input, optionally hiding input for secrets."""
        if is_secret:
            return getpass.getpass(f"{prompt} [{key}]: ")
        else:
            return input(f"{prompt} [{key}]: ")

    def get_progress(self):
        """Get current execution progress (optional UI method)"""
        executed_steps = len([r for r in self.results if r.executed])
        return executed_steps / len(self.steps) if self.steps else 0

    def get_current_status(self):
        """Get current status for UI (optional)"""
        return {
            "progress": self.get_progress(),
            "completed_steps": len([r for r in self.results if r.executed]),
            "total_steps": len(self.steps),
            "current_step": self.steps[len(self.results)]["name"] if self.steps and len(self.results) < len(
                self.steps) else None
        }

    def get_results_dict(self):
        """Get results as dictionary for UI (optional)"""
        return [
            {
                "name": r.name,
                "success": r.success,
                "message": r.message,
                "skipped": r.skipped,
                "executed": r.executed,
                "time_taken": r.time_taken,
                "attempts": r.attempts,
                "data": r.data,
            }
            for r in self.results
        ]


def print_summary(results: List[StepResult], verbose: bool = False, output_format: str = "rich"):
    """Print detailed summary table with timing"""
    if output_format == "json":
        summary = {
            "steps": [],
            "stats": {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "total_time": 0.0
            }
        }

        for result in results:
            step_data = {
                "name": result.name,
                "status": "skipped" if result.skipped else "success" if result.success else "failed",
                "time_taken": result.time_taken,
                "message": result.message,
                "attempts": result.attempts
            }
            summary["steps"].append(step_data)

            if result.executed:
                if result.success:
                    summary["stats"]["passed"] += 1
                else:
                    summary["stats"]["failed"] += 1
                summary["stats"]["total_time"] += result.time_taken
            else:
                summary["stats"]["skipped"] += 1

        return json.dumps(summary, indent=2)

    # Rich text output
    table = Table(title="\nWorkflow Summary", show_header=True, header_style="bold blue")
    table.add_column("Step", style="dim", width=20)
    table.add_column("Status", width=12)
    table.add_column("Time (s)", justify="right", width=10)
    table.add_column("Attempts", width=8)
    table.add_column("Details", width=50)

    for result in results:
        name = result.name
        time_taken = f"{result.time_taken:.2f}" if result.executed else "-"
        attempts = str(result.attempts) if result.executed else "-"

        # Truncate long messages
        details = result.message
        if not verbose and len(details) > 100:
            details = details[:100] + "..."

        if result.skipped:
            status = "[yellow]Skipped[/]"
        elif result.success:
            status = "[green]Success[/]"
        else:
            status = "[red]Failed[/]"

        table.add_row(name, status, time_taken, attempts, details)

    console.print(table)

    # Count statistics
    executed = [s for s in results if s.executed]
    successes = [s for s in executed if s.success]
    failures = [s for s in executed if not s.success]
    skipped = [s for s in results if s.skipped]

    console.print(
        f"\n[bold]Results:[/] [green]{len(successes)} passed[/], "
        f"[red]{len(failures)} failed[/], "
        f"[yellow]{len(skipped)} skipped[/]"
    )

    # Print total time
    total_time = sum(r.time_taken for r in executed)
    console.print(f"Total execution time: [bold]{total_time:.2f}s[/]")


def get_config_value(key: str, prompt: str, hide_input: bool = False) -> str:
    """Get value from environment or prompt user."""
    value = os.getenv(key)
    if value:
        return value

    if hide_input:
        import getpass
        return getpass.getpass(prompt)
    else:
        return input(prompt)