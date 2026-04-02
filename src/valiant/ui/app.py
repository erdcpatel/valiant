"""
Taipy GUI application.

Runs as a standalone process on port 8501.
Calls the Valiant core directly (no REST API needed for the UI).
"""
from __future__ import annotations

from typing import Any

import structlog

from valiant.core.exceptions import WorkflowNotFoundError, WorkflowValidationError
from valiant.core.models import StepResult, WorkflowResult
from valiant.core.registry import registry
from valiant.core.runner import WorkflowRunner
from valiant.storage import RunRepository, get_session, init_db
from valiant.ui.pages.dashboard import dashboard_md
from valiant.ui.pages.history import history_md
from valiant.ui.pages.workflows import workflows_md

log = structlog.get_logger(__name__)

# ── State variables (Taipy binds these by name) ───────────────────────────────

# Dashboard
total_runs: int = 0
success_runs: int = 0
failed_runs: int = 0
success_rate: str = "0%"

# Workflow selector
workflow_names: list[str] = []
selected_workflow: str = ""
workflow_description: str = ""
workflow_tags: str = ""
workflow_version: str = ""

# Input form
input_fields: list[dict[str, Any]] = []
form_values: dict[str, Any] = {}
form_error: str = ""

# Execution state
is_running: bool = False
run_status: str = ""
run_status_label: str = ""
run_id: str = ""
current_step: str = ""
step_results: list[dict[str, Any]] = []
run_error: str = ""
run_duration: str = ""

# History
history_rows: list[dict[str, Any]] = []
history_filter_workflow: str = "All"
history_filter_status: str = "All"
history_limit: int = 50
history_workflow_options: list[str] = ["All"]
history_status_options: list[str] = ["All", "success", "partial", "failed"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_stats(state) -> None:
    session_gen = get_session()
    session = next(session_gen)
    try:
        repo = RunRepository(session)
        state.total_runs = repo.count_runs()
        state.success_runs = repo.count_runs(status="success")
        state.failed_runs = repo.count_runs(status="failed")
        rate = (state.success_runs / state.total_runs * 100) if state.total_runs else 0.0
        state.success_rate = f"{rate:.1f}%"
    except Exception as exc:
        log.warning("ui.stats_error", error=str(exc))
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


def _load_history(state) -> None:
    session_gen = get_session()
    session = next(session_gen)
    try:
        repo = RunRepository(session)
        wf_filter = None if state.history_filter_workflow == "All" else state.history_filter_workflow
        st_filter = None if state.history_filter_status == "All" else state.history_filter_status
        runs = repo.list_runs(
            workflow_name=wf_filter,
            status=st_filter,
            limit=int(state.history_limit),
        )
        state.history_rows = [r.to_dict() for r in runs]
    except Exception as exc:
        log.warning("ui.history_error", error=str(exc))
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


def _workflow_options_for_history(state) -> None:
    names = registry.names()
    state.history_workflow_options = ["All"] + names


# ── Taipy callbacks ───────────────────────────────────────────────────────────

def on_init(state) -> None:
    """Called once when a new user connects."""
    state.workflow_names = registry.names()
    state.history_workflow_options = ["All"] + registry.names()
    _load_stats(state)
    _load_history(state)


def on_workflow_selected(state, _var, value) -> None:
    """Called when user selects a workflow from the dropdown."""
    name = value
    if not name:
        return
    try:
        meta = registry.get_meta(name)
        state.workflow_description = meta.description or "*No description provided.*"
        state.workflow_tags = ", ".join(meta.tags) if meta.tags else "—"
        state.workflow_version = meta.version

        # Build input fields table
        fields_display = [
            {
                "label": f.display_label(),
                "type": f.type.value,
                "required": "Yes" if f.required else "No",
                "default": str(f.default) if f.default is not None else "",
                "description": f.description,
            }
            for f in meta.input_fields
        ]
        state.input_fields = fields_display

        # Reset form values to defaults
        defaults = {}
        for f in meta.input_fields:
            if f.default is not None:
                defaults[f.name] = f.default
            elif f.type.value == "boolean":
                defaults[f.name] = False
            elif f.type.value == "number":
                defaults[f.name] = 0
            else:
                defaults[f.name] = ""
        state.form_values = defaults

        # Reset execution state
        state.step_results = []
        state.run_status = ""
        state.run_status_label = ""
        state.run_error = ""
        state.form_error = ""
    except WorkflowNotFoundError:
        state.workflow_description = "Workflow not found."


def on_run_workflow(state, _id=None, _payload=None) -> None:
    """Called when user clicks Run Workflow."""
    if not state.selected_workflow or state.is_running:
        return

    state.is_running = True
    state.run_status = "running"
    state.run_status_label = "⏳ Running..."
    state.step_results = []
    state.run_error = ""
    state.form_error = ""

    try:
        workflow_cls = registry.get_class(state.selected_workflow)
        inputs = dict(state.form_values) if state.form_values else {}

        collected: list[dict[str, Any]] = []

        def on_step_done(result: StepResult) -> None:
            collected.append(result.to_display_dict())
            state.step_results = list(collected)
            state.current_step = result.name

        runner = WorkflowRunner(on_step_complete=on_step_done)
        result: WorkflowResult = runner.run(workflow_cls, inputs, triggered_by="ui")

        state.step_results = [s.to_display_dict() for s in result.steps]
        state.run_id = f"Run {result.run_id[:8]}"
        state.run_status = result.status_label
        state.run_duration = f"{result.total_duration_ms:.0f}ms"

        if result.success:
            state.run_status_label = f"✅ Completed in {result.total_duration_ms:.0f}ms"
        elif result.status_label == "partial":
            state.run_status_label = f"⚠️ Partial success — {result.total_duration_ms:.0f}ms"
        else:
            state.run_status_label = f"❌ Failed — {result.total_duration_ms:.0f}ms"

        # Persist
        session_gen = get_session()
        session = next(session_gen)
        try:
            repo = RunRepository(session)
            sensitive = {f.name for f in registry.get_meta(state.selected_workflow).input_fields if f.sensitive}
            repo.save_with_inputs(result, inputs, sensitive)
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

        _load_stats(state)

    except WorkflowValidationError as exc:
        state.form_error = str(exc)
        state.run_status = "failed"
        state.run_status_label = "❌ Validation error"
    except Exception as exc:
        state.run_error = str(exc)
        state.run_status = "failed"
        state.run_status_label = "❌ Error"
        log.exception("ui.run_error", workflow=state.selected_workflow, error=str(exc))
    finally:
        state.is_running = False


def on_history_filter_change(state, _var=None, _value=None) -> None:
    _load_history(state)


def on_history_refresh(state, _id=None, _payload=None) -> None:
    _load_history(state)
    _load_stats(state)


# ── App entry point ───────────────────────────────────────────────────────────

def run_ui(port: int = 8501, debug: bool = False) -> None:
    from valiant.logging_setup import configure_logging
    configure_logging()
    init_db()
    registry.load_builtins()

    try:
        from taipy.gui import Gui
    except ImportError:
        print("taipy-gui is not installed. Run: pip install taipy-gui")
        raise

    pages = {
        "/": dashboard_md,
        "workflows": workflows_md,
        "history": history_md,
    }

    gui = Gui(pages=pages)
    gui.run(
        title="Valiant",
        port=port,
        debug=debug,
        dark_mode=False,
        use_reloader=False,
    )
