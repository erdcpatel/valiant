"""
WorkflowRunner — synchronous execution engine.

Uses ThreadPoolExecutor for parallel step groups.
No asyncio.run() calls — safe to call from any context including Taipy callbacks.
"""
from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, Generator, Iterator

import structlog

from valiant.config import settings
from valiant.core.context import WorkflowContext
from valiant.core.exceptions import StepExecutionError, WorkflowValidationError
from valiant.core.models import StepResult, WorkflowResult
from valiant.core.workflow import StepConfig, Workflow

log = structlog.get_logger(__name__)


class WorkflowRunner:
    """
    Executes a workflow instance synchronously.

    Supports:
    - Sequential and parallel step groups
    - Per-step retries and timeouts
    - Step dependency ordering
    - Progress streaming via generator
    - Optional result persistence callback
    """

    def __init__(
        self,
        max_workers: int | None = None,
        stop_on_failure: bool = True,
        on_step_complete: Callable[[StepResult], None] | None = None,
    ) -> None:
        self._max_workers = max_workers or settings.max_parallel_steps
        self._stop_on_failure = stop_on_failure
        self._on_step_complete = on_step_complete

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        workflow_cls: type[Workflow],
        inputs: dict[str, Any],
        triggered_by: str = "unknown",
    ) -> WorkflowResult:
        """Execute a workflow and return the final WorkflowResult."""
        results = list(self._execute(workflow_cls, inputs, triggered_by))
        # The last yielded item is the WorkflowResult
        final = results[-1] if results else None
        if isinstance(final, WorkflowResult):
            return final
        # Fallback: build result from step results
        steps = [r for r in results if isinstance(r, StepResult)]
        return WorkflowResult(
            workflow_name=getattr(workflow_cls, "_workflow_name", workflow_cls.__name__),
            success=all(s.success or s.skipped for s in steps),
            steps=steps,
            triggered_by=triggered_by,
        )

    def run_streaming(
        self,
        workflow_cls: type[Workflow],
        inputs: dict[str, Any],
        triggered_by: str = "unknown",
    ) -> Iterator[StepResult | WorkflowResult]:
        """
        Generator that yields each StepResult as it completes, then the final WorkflowResult.

        Usage::

            for item in runner.run_streaming(MyWorkflow, inputs):
                if isinstance(item, StepResult):
                    print(f"  {item.name}: {item.status_label}")
                elif isinstance(item, WorkflowResult):
                    print(f"Run {item.run_id}: {item.status_label}")
        """
        yield from self._execute(workflow_cls, inputs, triggered_by)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _execute(
        self,
        workflow_cls: type[Workflow],
        inputs: dict[str, Any],
        triggered_by: str,
    ) -> Generator[StepResult | WorkflowResult, None, None]:
        wf_name = getattr(workflow_cls, "_workflow_name", workflow_cls.__name__)
        log.info("workflow.start", workflow=wf_name, triggered_by=triggered_by)

        # Instantiate workflow and validate inputs
        instance = workflow_cls()
        errors = instance.validate_inputs(inputs)
        if errors:
            raise WorkflowValidationError(errors)

        ctx = WorkflowContext(inputs=inputs, workflow_name=wf_name)
        started_at = datetime.now(timezone.utc)
        run_start = time.perf_counter()
        all_steps: list[StepResult] = []
        abort = False

        # Discover and group steps
        step_defs = workflow_cls.discover_steps()
        groups = self._group_steps(step_defs)

        for group in groups:
            if abort:
                # Emit skipped results for remaining steps
                for _, cfg in group:
                    result = StepResult(name=cfg.name, success=True, skipped=True,
                                        message="Skipped — earlier step failed")
                    all_steps.append(result)
                    yield result
                continue

            if len(group) == 1:
                func, cfg = group[0]
                result = self._run_step_with_retry(instance, func, cfg, ctx)
                ctx._record_result(result)
                all_steps.append(result)
                if self._on_step_complete:
                    self._on_step_complete(result)
                yield result
                if not result.success and not result.skipped and self._stop_on_failure:
                    abort = True
            else:
                # Parallel group
                parallel_results = self._run_parallel(instance, group, ctx)
                for result in parallel_results:
                    ctx._record_result(result)
                    all_steps.append(result)
                    if self._on_step_complete:
                        self._on_step_complete(result)
                    yield result
                    if not result.success and not result.skipped and self._stop_on_failure:
                        abort = True

        total_ms = (time.perf_counter() - run_start) * 1000
        final = WorkflowResult(
            workflow_name=wf_name,
            success=all(s.success or s.skipped for s in all_steps),
            steps=all_steps,
            total_duration_ms=total_ms,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            triggered_by=triggered_by,
        )
        log.info("workflow.complete", workflow=wf_name, status=final.status_label,
                 duration_ms=round(total_ms, 1))
        yield final

    def _group_steps(
        self, step_defs: list[tuple]
    ) -> list[list[tuple]]:
        """
        Group steps for execution order.
        Steps with the same parallel_group run concurrently.
        Others run sequentially by order.
        """
        from collections import defaultdict

        ordered: list[list[tuple]] = []
        seen_orders: dict[int, dict[str | None, list]] = defaultdict(lambda: defaultdict(list))

        for func, cfg in step_defs:
            seen_orders[cfg.order][cfg.parallel_group].append((func, cfg))

        for order in sorted(seen_orders.keys()):
            groups_at_order = seen_orders[order]
            for group_name, members in groups_at_order.items():
                if group_name is None:
                    # Each step in its own sequential slot
                    for member in members:
                        ordered.append([member])
                else:
                    ordered.append(members)

        return ordered

    def _run_parallel(
        self,
        instance: Workflow,
        group: list[tuple],
        ctx: WorkflowContext,
    ) -> list[StepResult]:
        """Run a group of steps concurrently and return results in completion order."""
        results: list[StepResult] = []
        with ThreadPoolExecutor(max_workers=min(len(group), self._max_workers)) as executor:
            future_to_cfg: dict[Future, StepConfig] = {
                executor.submit(self._run_step_with_retry, instance, func, cfg, ctx): cfg
                for func, cfg in group
            }
            for future in as_completed(future_to_cfg):
                try:
                    results.append(future.result())
                except Exception as exc:
                    cfg = future_to_cfg[future]
                    results.append(StepResult(
                        name=cfg.name, success=False,
                        message=f"Unhandled error: {exc}", error=str(exc)
                    ))
        return results

    def _run_step_with_retry(
        self,
        instance: Workflow,
        func,
        cfg: StepConfig,
        ctx: WorkflowContext,
    ) -> StepResult:
        """Execute a step with retry logic. Returns the final StepResult."""
        max_attempts = max(1, cfg.retries)
        last_result: StepResult | None = None

        for attempt in range(1, max_attempts + 1):
            started = time.perf_counter()
            try:
                result = func(instance, ctx)
                duration_ms = (time.perf_counter() - started) * 1000
                result = result.model_copy(update={"duration_ms": duration_ms, "attempts": attempt})

                if result.success or result.skipped:
                    log.debug("step.success", step=cfg.name, attempt=attempt,
                               duration_ms=round(duration_ms, 1))
                    return result

                log.warning("step.failed", step=cfg.name, attempt=attempt,
                            message=result.message)
                last_result = result

            except Exception as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                log.warning("step.exception", step=cfg.name, attempt=attempt, error=str(exc))
                last_result = StepResult(
                    name=cfg.name,
                    success=False,
                    message=f"Exception: {exc}",
                    error=str(exc),
                    duration_ms=duration_ms,
                    attempts=attempt,
                )

        assert last_result is not None
        return last_result.model_copy(update={"attempts": max_attempts})
