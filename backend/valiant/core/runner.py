"""
Async Workflow Runner with parallel execution, retries, smart resume, and live event callbacks.
"""
import asyncio
import time
import uuid
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Awaitable, Union
from concurrent.futures import ThreadPoolExecutor
import inspect
import json

from .models import (
    WorkflowResult,
    WorkflowStatus,
    StepResult,
    StepStatus,
    StepConfig,
    StepContextDelta,
    StepLineage,
    RunEvent,
    RunEventType,
)
from .context import WorkflowContext
from .workflow import Workflow

_ACTIVE_RUNNERS: Dict[str, "WorkflowRunner"] = {}
_APPROVAL_EVENTS: Dict[str, Dict[str, asyncio.Event]] = {}
_APPROVAL_DECISIONS: Dict[str, Dict[str, Dict[str, Any]]] = {}


def get_active_runner(run_id: str) -> Optional["WorkflowRunner"]:
    """Retrieve in-memory runner for an active workflow execution."""
    return _ACTIVE_RUNNERS.get(run_id)


def signal_step_approval(
    run_id: str,
    step_name: str,
    approved: bool,
    approver: Optional[str] = None,
    notes: Optional[str] = None
) -> bool:
    """Signal human approval or rejection to a suspended in-memory runner."""
    events = _APPROVAL_EVENTS.get(run_id, {})
    if step_name in events:
        if run_id not in _APPROVAL_DECISIONS:
            _APPROVAL_DECISIONS[run_id] = {}
        _APPROVAL_DECISIONS[run_id][step_name] = {
            "approved": approved,
            "approved_by": approver or "operator",
            "notes": notes or "",
            "approved_at": datetime.utcnow().isoformat()
        }
        events[step_name].set()
        return True
    return False


class WorkflowRunner:
    """
    Executes a Workflow with concurrency control, timeouts, retries,
    smart resume from failed steps, and real-time event streaming.
    """

    def __init__(
        self,
        workflow: Workflow,
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        resumed_from_step: Optional[str] = None,
        stop_on_failure: bool = True,
        on_event: Optional[Callable[[RunEvent], Union[None, Awaitable[None]]]] = None,
        environment: str = "dev",
        profile: Optional[str] = None
    ):
        self.workflow = workflow
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"
        self.parent_run_id = parent_run_id
        self.resumed_from_step = resumed_from_step
        self.stop_on_failure = stop_on_failure
        self.on_event = on_event
        self.environment = environment
        self.profile = profile
        self.cancelled = False
        self.approved_steps: Dict[str, Dict[str, Any]] = {}
        self._thread_pool = ThreadPoolExecutor(max_workers=8)

    async def _emit(self, event_type: RunEventType, step_name: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Emit real-time event to registered listener."""
        if not self.on_event:
            return
        event = RunEvent(
            run_id=self.run_id,
            event_type=event_type,
            step_name=step_name,
            data=data or {}
        )
        try:
            if inspect.iscoroutinefunction(self.on_event):
                await self.on_event(event)
            else:
                self.on_event(event)
        except Exception as e:
            # Prevent logging errors from crashing execution
            print(f"[Runner Event Error] {e}")

    def cancel(self):
        """Request cancellation of the current run."""
        self.cancelled = True

    async def run(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        resume_from_step: Optional[str] = None,
        pre_seeded_context: Optional[Dict[str, Any]] = None,
        reused_step_results: Optional[List[StepResult]] = None,
        approved_steps: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> WorkflowResult:
        """Execute the workflow lifecycle with optional smart resume."""
        if approved_steps:
            self.approved_steps.update(approved_steps)
        _ACTIVE_RUNNERS[self.run_id] = self
        inputs = inputs or {}
        resume_target = resume_from_step or self.resumed_from_step
        context = WorkflowContext()

        # 1. Populate context with workflow schema defaults
        for field in self.workflow.inputs():
            if field.default is not None:
                context[field.name] = field.default
            if field.sensitive:
                context.mark_sensitive(field.name)

        # 1b. Inject environment profile presets if defined on workflow
        if hasattr(self.workflow, "get_profiles"):
            profiles = self.workflow.get_profiles()
            preset_key = self.profile or self.environment
            if preset_key in profiles and isinstance(profiles[preset_key], dict):
                for k, v in profiles[preset_key].items():
                    context[k] = v

        context["__environment__"] = self.environment
        context["__profile__"] = self.profile or self.environment

        # 2. If pre-seeded context is provided from parent run, re-hydrate intermediate state
        if pre_seeded_context:
            for k, v in pre_seeded_context.items():
                context[k] = v

        # 3. Apply provided inputs (overriding defaults, profile presets, and previous context)
        for k, v in inputs.items():
            if v is not None and v != "":
                context[k] = v

        steps_with_config = self.workflow.get_steps()
        total_steps = len(steps_with_config)
        step_results: List[StepResult] = []
        self.step_results = step_results
        self.context = context
        self.inputs = inputs

        reused_map: Dict[str, StepResult] = {r.name: r for r in (reused_step_results or [])}
        initial_steps: List[Dict[str, Any]] = []
        for cfg, _ in steps_with_config:
            if cfg.name in reused_map:
                prev = reused_map[cfg.name]
                initial_steps.append({
                    "name": cfg.name,
                    "order": cfg.order,
                    "tags": cfg.tags,
                    "parallel_group": cfg.parallel_group,
                    "requires": cfg.requires,
                    "condition": cfg.condition,
                    "status": "success",
                    "success": True,
                    "reused": True,
                    "skipped": False,
                    "time_taken": 0.0,
                    "message": f"[Reused from parent run] {prev.message or 'Completed'}",
                    "context_snapshot": prev.context_snapshot or {}
                })
            else:
                initial_steps.append({
                    "name": cfg.name,
                    "order": cfg.order,
                    "tags": cfg.tags,
                    "parallel_group": cfg.parallel_group,
                    "requires": cfg.requires,
                    "condition": cfg.condition,
                    "status": "pending",
                    "requires_approval": getattr(cfg, "requires_approval", False),
                    "approval_prompt": getattr(cfg, "approval_prompt", None),
                    "success": False,
                    "reused": False,
                    "skipped": False,
                    "time_taken": 0.0,
                    "message": "Approval required before execution" if getattr(cfg, "requires_approval", False) else "Waiting in queue"
                })

        self.initial_steps = initial_steps

        start_time = time.time()
        start_iso = datetime.utcnow().isoformat()
        self.started_at = start_iso

        await self._emit(RunEventType.RUN_STARTED, data={
            "workflow_name": getattr(self.workflow, "workflow_id", self.workflow.__class__.__name__),
            "total_steps": total_steps,
            "steps": initial_steps,
            "inputs": context.to_dict(mask_secrets=True),
            "parent_run_id": self.parent_run_id,
            "resumed_from_step": resume_target
        })

        # Run workflow setup hook
        try:
            self.workflow.setup(context)
        except Exception as e:
            error_msg = f"Workflow setup failed: {str(e)}"
            await self._emit(RunEventType.RUN_FINISHED, data={"error": error_msg, "success": False})
            return WorkflowResult(
                workflow_name=getattr(self.workflow, "workflow_id", self.workflow.__class__.__name__),
                run_id=self.run_id,
                parent_run_id=self.parent_run_id,
                resumed_from_step=resume_target,
                status=WorkflowStatus.FAILED,
                success=False,
                error=error_msg,
                started_at=start_iso,
                completed_at=datetime.utcnow().isoformat(),
                context=context.to_dict(mask_secrets=True)
            )

        has_failure = False

        # Group steps into execution batches (parallel groups execute together)
        grouped_steps: List[List[tuple[StepConfig, Callable]]] = []
        current_group: List[tuple[StepConfig, Callable]] = []
        current_group_name: Optional[str] = None

        for config, func in steps_with_config:
            if config.parallel_group:
                if current_group_name == config.parallel_group:
                    current_group.append((config, func))
                else:
                    if current_group:
                        grouped_steps.append(current_group)
                    current_group = [(config, func)]
                    current_group_name = config.parallel_group
            else:
                if current_group:
                    grouped_steps.append(current_group)
                    current_group = []
                    current_group_name = None
                grouped_steps.append([(config, func)])

        if current_group:
            grouped_steps.append(current_group)

        # Smart Resume Trackers
        resume_reached = (resume_target is None)
        reused_map: Dict[str, StepResult] = {r.name: r for r in (reused_step_results or [])}

        # Execute batches
        for batch in grouped_steps:
            if self.cancelled:
                for config, _ in batch:
                    skip_res = StepResult(
                        name=config.name,
                        status=StepStatus.SKIPPED,
                        message="Cancelled by user",
                        skipped=True
                    )
                    step_results.append(skip_res)
                    await self._emit(RunEventType.STEP_FINISHED, step_name=config.name, data=skip_res.model_dump())
                continue

            # Check if this batch is prior to the resume target
            batch_step_names = [config.name for config, _ in batch]
            if not resume_reached:
                if resume_target in batch_step_names:
                    # We reached the target step!
                    resume_reached = True
                else:
                    # This batch is prior to resume target -> Reuse cached results!
                    for config, _ in batch:
                        if config.name in reused_map:
                            prev = reused_map[config.name]
                            cached_res = StepResult(
                                name=config.name,
                                order=config.order,
                                parallel_group=config.parallel_group,
                                requires=list(config.requires),
                                condition=config.condition,
                                status=StepStatus.SUCCESS,
                                success=True,
                                message=f"[Reused from parent run] {prev.message or 'Completed'}",
                                data=prev.data,
                                metrics=prev.metrics,
                                tags=config.tags,
                                logs=prev.logs,
                                time_taken=0.0,
                                executed=True,
                                reused=True,
                                context_snapshot=prev.context_snapshot
                            )
                        else:
                            cached_res = StepResult(
                                name=config.name,
                                order=config.order,
                                parallel_group=config.parallel_group,
                                requires=list(config.requires),
                                condition=config.condition,
                                status=StepStatus.SUCCESS,
                                success=True,
                                message="[Reused from parent run] Cached prerequisite",
                                tags=config.tags,
                                time_taken=0.0,
                                executed=True,
                                reused=True
                            )
                        step_results.append(cached_res)
                        await self._emit(RunEventType.STEP_FINISHED, step_name=config.name, data=cached_res.model_dump())
                    continue

            # Check for Breakpoints / Manual Approvals
            approval_aborted = False
            for config, _ in batch:
                if config.requires_approval and config.name not in self.approved_steps:
                    # 1. Update database to waiting_approval
                    try:
                        from ..db.database import get_session, WorkflowRunRecord, StepRunRecord
                        with get_session(self.environment) as session:
                            run_rec = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == self.run_id).first()
                            if run_rec:
                                run_rec.status = "waiting_approval"
                                run_rec.context_json = json.dumps(context.to_dict(mask_secrets=True))
                            else:
                                run_rec = WorkflowRunRecord(
                                    id=self.run_id,
                                    workflow_name=getattr(self.workflow, "workflow_id", self.workflow.__class__.__name__),
                                    status="waiting_approval",
                                    started_at=start_iso,
                                    environment=self.environment,
                                    context_json=json.dumps(context.to_dict(mask_secrets=True))
                                )
                                session.add(run_rec)

                            step_rec = session.query(StepRunRecord).filter(
                                StepRunRecord.run_id == self.run_id,
                                StepRunRecord.name == config.name
                            ).first()
                            if step_rec:
                                step_rec.status = "waiting_approval"
                                step_rec.requires_approval = True
                                step_rec.approval_prompt = config.approval_prompt
                                step_rec.context_snapshot_json = json.dumps(context.to_dict(mask_secrets=True))
                            else:
                                step_rec = StepRunRecord(
                                    run_id=self.run_id,
                                    name=config.name,
                                    order=config.order,
                                    status="waiting_approval",
                                    requires_approval=True,
                                    approval_prompt=config.approval_prompt,
                                    context_snapshot_json=json.dumps(context.to_dict(mask_secrets=True))
                                )
                                session.add(step_rec)
                            session.commit()
                    except Exception as dbe:
                        print(f"[Approval DB Notice] {dbe}")

                    # 1b. Update in-memory initial_steps
                    for s in getattr(self, "initial_steps", []):
                        if s.get("name") == config.name:
                            s["status"] = "waiting_approval"
                            s["message"] = f"Waiting for operator approval: {config.approval_prompt or ''}".strip()
                            s["requires_approval"] = True
                            s["approval_prompt"] = config.approval_prompt
                            break

                    # 2. Emit STEP_WAITING_APPROVAL event
                    await self._emit(
                        RunEventType.STEP_WAITING_APPROVAL,
                        step_name=config.name,
                        data={
                            "step_name": config.name,
                            "approval_prompt": config.approval_prompt,
                            "approval_roles": config.approval_roles,
                            "context": context.to_dict(mask_secrets=True),
                            "status": "waiting_approval"
                        }
                    )

                    # 3. Create Event & Wait for signal or cancellation
                    if self.run_id not in _APPROVAL_EVENTS:
                        _APPROVAL_EVENTS[self.run_id] = {}
                    app_event = asyncio.Event()
                    _APPROVAL_EVENTS[self.run_id][config.name] = app_event

                    while not app_event.is_set() and not self.cancelled:
                        try:
                            await asyncio.wait_for(app_event.wait(), timeout=1.0)
                        except asyncio.TimeoutError:
                            pass

                    if self.cancelled:
                        skip_res = StepResult(
                            name=config.name,
                            order=config.order,
                            status=StepStatus.SKIPPED,
                            message="Cancelled while awaiting approval",
                            skipped=True,
                            requires_approval=True
                        )
                        step_results.append(skip_res)
                        await self._emit(RunEventType.STEP_FINISHED, step_name=config.name, data=skip_res.model_dump())
                        has_failure = True
                        approval_aborted = True
                        break

                    decision = _APPROVAL_DECISIONS.get(self.run_id, {}).get(config.name, {})
                    if not decision.get("approved"):
                        # Rejected by operator
                        for s in getattr(self, "initial_steps", []):
                            if s.get("name") == config.name:
                                s["status"] = "rejected"
                                s["message"] = f"Rejected: {decision.get('notes') or 'No reason provided'}"
                                s["approved_by"] = decision.get("approved_by")
                                break

                        rej_res = StepResult(
                            name=config.name,
                            order=config.order,
                            parallel_group=config.parallel_group,
                            requires=list(config.requires),
                            condition=config.condition,
                            status=StepStatus.REJECTED,
                            success=False,
                            executed=True,
                            message=f"Rejected by {decision.get('approved_by', 'operator')}: {decision.get('notes') or 'No reason provided'}",
                            requires_approval=True,
                            approval_prompt=config.approval_prompt,
                            approved_by=decision.get("approved_by"),
                            approved_at=decision.get("approved_at"),
                            approval_notes=decision.get("notes"),
                            tags=config.tags
                        )
                        step_results.append(rej_res)
                        await self._emit(RunEventType.STEP_REJECTED, step_name=config.name, data=rej_res.model_dump())
                        await self._emit(RunEventType.STEP_FINISHED, step_name=config.name, data=rej_res.model_dump())
                        has_failure = True
                        approval_aborted = True
                        break

                    # Approved!
                    for s in getattr(self, "initial_steps", []):
                        if s.get("name") == config.name:
                            s["status"] = "running"
                            s["message"] = f"Approved by {decision.get('approved_by', 'operator')}"
                            s["approved_by"] = decision.get("approved_by")
                            s["approved_at"] = decision.get("approved_at")
                            s["approval_notes"] = decision.get("notes")
                            break

                    self.approved_steps[config.name] = decision
                    try:
                        from ..db.database import get_session, WorkflowRunRecord
                        with get_session(self.environment) as session:
                            run_rec = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == self.run_id).first()
                            if run_rec:
                                run_rec.status = "running"
                            session.commit()
                    except Exception:
                        pass
                    await self._emit(RunEventType.STEP_APPROVED, step_name=config.name, data=decision)

            if approval_aborted:
                break

            # Run batch steps concurrently
            tasks = [self._execute_single_step(config, func, context, step_results, has_failure) for config, func in batch]
            batch_results = await asyncio.gather(*tasks)

            for res in batch_results:
                step_results.append(res)
                if res.executed and not res.success:
                    has_failure = True

        # Run teardown hook
        try:
            self.workflow.teardown(context)
        except Exception:
            pass

        total_time = round(time.time() - start_time, 3)
        completed_iso = datetime.utcnow().isoformat()

        executed_count = sum(1 for r in step_results if r.executed)
        successful_count = sum(1 for r in step_results if r.success and r.executed)
        failed_count = sum(1 for r in step_results if not r.success and r.executed)
        skipped_count = sum(1 for r in step_results if r.skipped)

        overall_status = WorkflowStatus.COMPLETED
        if self.cancelled:
            overall_status = WorkflowStatus.CANCELLED
        elif failed_count > 0:
            overall_status = WorkflowStatus.FAILED

        overall_success = (failed_count == 0 and not self.cancelled)

        # Compute Bidirectional Data Lineage across executed steps
        key_producer_map: Dict[str, str] = {}
        for k in (inputs or {}).keys():
            key_producer_map[k] = "Workflow Inputs"
        if hasattr(self.workflow, "inputs"):
            for f in self.workflow.inputs():
                if f.name not in key_producer_map:
                    key_producer_map[f.name] = "Default Parameter"
        key_producer_map["__environment__"] = "Platform Runtime"
        key_producer_map["__profile__"] = "Environment Preset"

        # 1. Populate upstream sources for each step
        for res in step_results:
            if res.context_delta:
                upstream: Dict[str, str] = {}
                for rk in res.context_delta.reads:
                    upstream[rk] = key_producer_map.get(rk, "Workflow Inputs")

                # Register this step as the producer of keys it added or modified
                for ak in res.context_delta.added.keys():
                    key_producer_map[ak] = res.name
                for mk in res.context_delta.modified.keys():
                    key_producer_map[mk] = res.name

                res.lineage = StepLineage(upstream_sources=upstream, downstream_targets={})

        # 2. Populate downstream targets for each step
        for idx, res in enumerate(step_results):
            if res.lineage and res.context_delta:
                produced_keys = set(res.context_delta.added.keys()) | set(res.context_delta.modified.keys())
                downstream: Dict[str, List[str]] = {}
                for pk in produced_keys:
                    consumers: List[str] = []
                    for later_res in step_results[idx + 1:]:
                        if later_res.context_delta and pk in later_res.context_delta.reads:
                            if later_res.name not in consumers:
                                consumers.append(later_res.name)
                    if consumers:
                        downstream[pk] = consumers
                res.lineage.downstream_targets = downstream

        wf_result = WorkflowResult(
            workflow_name=getattr(self.workflow, "workflow_id", self.workflow.__class__.__name__),
            run_id=self.run_id,
            parent_run_id=self.parent_run_id,
            resumed_from_step=resume_target,
            status=overall_status,
            success=overall_success,
            total_steps=total_steps,
            executed_steps=executed_count,
            successful_steps=successful_count,
            failed_steps=failed_count,
            skipped_steps=skipped_count,
            total_time=total_time,
            started_at=start_iso,
            completed_at=completed_iso,
            results=step_results,
            context=context.to_dict(mask_secrets=True),
            environment=self.environment,
            profile=self.profile
        )

        await self._emit(RunEventType.RUN_FINISHED, data=wf_result.model_dump())
        return wf_result

    async def _execute_single_step(
        self,
        config: StepConfig,
        func: Callable,
        context: WorkflowContext,
        previous_results: List[StepResult],
        prior_failure: bool
    ) -> StepResult:
        """Executes a single step with dependency check, condition check, and retry loop."""
        step_name = config.name

        # 1. Dependency check
        successful_steps = {r.name for r in previous_results if r.success and r.executed}
        missing_dependencies = [dep for dep in config.requires if dep not in successful_steps]
        if missing_dependencies:
            res = StepResult(
                name=step_name,
                order=config.order,
                parallel_group=config.parallel_group,
                requires=list(config.requires),
                condition=config.condition,
                status=StepStatus.SKIPPED,
                message=f"Missing dependencies: {', '.join(missing_dependencies)}",
                skipped=True,
                tags=config.tags,
                context_snapshot=context.to_dict(mask_secrets=True)
            )
            await self._emit(RunEventType.STEP_FINISHED, step_name=step_name, data=res.model_dump())
            return res

        # 2. Stop on failure check
        if prior_failure and self.stop_on_failure:
            res = StepResult(
                name=step_name,
                order=config.order,
                parallel_group=config.parallel_group,
                requires=list(config.requires),
                condition=config.condition,
                status=StepStatus.SKIPPED,
                message="Skipped due to earlier step failure",
                skipped=True,
                tags=config.tags,
                context_snapshot=context.to_dict(mask_secrets=True)
            )
            await self._emit(RunEventType.STEP_FINISHED, step_name=step_name, data=res.model_dump())
            return res

        # 3. Condition check
        if config.condition:
            cond_val = context.get(config.condition)
            if not cond_val:
                res = StepResult(
                    name=step_name,
                    order=config.order,
                    parallel_group=config.parallel_group,
                    requires=list(config.requires),
                    condition=config.condition,
                    status=StepStatus.SKIPPED,
                    message=f"Condition '{config.condition}' evaluated to False/empty",
                    skipped=True,
                    tags=config.tags,
                    context_snapshot=context.to_dict(mask_secrets=True)
                )
                await self._emit(RunEventType.STEP_FINISHED, step_name=step_name, data=res.model_dump())
                return res

        # Step is ready to run
        context_before = context.to_dict(mask_secrets=True)
        step_context = context.scoped(step_name)

        await self._emit(RunEventType.STEP_STARTED, step_name=step_name, data={"order": config.order})

        attempts = 0
        max_attempts = config.retries + 1
        step_start_time = time.time()
        final_result: Optional[StepResult] = None

        while attempts < max_attempts:
            attempts += 1
            try:
                # Call step method with scoped step context
                if inspect.iscoroutinefunction(func):
                    res = await asyncio.wait_for(func(step_context), timeout=config.timeout)
                else:
                    loop = asyncio.get_running_loop()
                    res = await asyncio.wait_for(
                        loop.run_in_executor(self._thread_pool, func, step_context),
                        timeout=config.timeout
                    )

                # Format return value
                if isinstance(res, StepResult):
                    final_result = res
                elif isinstance(res, tuple) and len(res) >= 2:
                    ok = bool(res[0])
                    msg = str(res[1])
                    data = res[2] if len(res) > 2 else None
                    final_result = StepResult(
                        name=step_name,
                        status=StepStatus.SUCCESS if ok else StepStatus.FAILED,
                        success=ok,
                        message=msg,
                        data=data
                    )
                else:
                    final_result = StepResult(
                        name=step_name,
                        status=StepStatus.SUCCESS,
                        success=True,
                        message=str(res) if res is not None else "Completed",
                        data=res
                    )

                if final_result.success:
                    break
                elif attempts < max_attempts:
                    await asyncio.sleep(0.5)

            except asyncio.TimeoutError:
                final_result = StepResult(
                    name=step_name,
                    status=StepStatus.FAILED,
                    success=False,
                    message=f"Timed out after {config.timeout}s",
                    error="TimeoutError"
                )
            except Exception as e:
                err_detail = traceback.format_exc()
                final_result = StepResult(
                    name=step_name,
                    status=StepStatus.FAILED,
                    success=False,
                    message=f"Error: {str(e)}",
                    error=err_detail
                )
                if attempts < max_attempts:
                    await asyncio.sleep(0.5)

        step_elapsed = round(time.time() - step_start_time, 3)
        context_after = context.to_dict(mask_secrets=True)
        telemetry = step_context.get_telemetry()

        # Compute context delta
        added: Dict[str, Any] = {}
        modified: Dict[str, Dict[str, Any]] = {}
        deleted: List[str] = []

        for k, v in context_after.items():
            if k not in context_before:
                added[k] = v
            elif context_before.get(k) != v:
                modified[k] = {
                    "before": context_before.get(k),
                    "after": v,
                }

        for k in context_before:
            if k not in context_after:
                deleted.append(k)

        delta = StepContextDelta(
            reads=telemetry.get("reads", []),
            added=added,
            modified=modified,
            deleted=deleted,
        )

        final_result.name = step_name
        final_result.order = config.order
        final_result.parallel_group = config.parallel_group
        final_result.requires = list(config.requires)
        final_result.condition = config.condition
        final_result.executed = True
        final_result.attempts = attempts
        final_result.time_taken = step_elapsed
        final_result.context_before = context_before
        final_result.context_snapshot = context_after
        final_result.context_delta = delta
        final_result.requires_approval = bool(config.requires_approval)
        final_result.approval_prompt = config.approval_prompt

        if config.name in self.approved_steps:
            app_dec = self.approved_steps[config.name]
            final_result.approved_by = app_dec.get("approved_by")
            final_result.approved_at = app_dec.get("approved_at")
            final_result.approval_notes = app_dec.get("notes")

        # Merge config tags
        for t in config.tags:
            if t not in final_result.tags:
                final_result.tags.append(t)

        # Check for Polars Tabular Data in return data or written context
        try:
            from .tabular import is_polars_dataframe, to_tabular_payload, save_tabular_artifact
            target_df = None
            if is_polars_dataframe(final_result.data):
                target_df = final_result.data
            else:
                for wk in telemetry.get("writes", []):
                    val = context.get(wk)
                    if is_polars_dataframe(val):
                        target_df = val
                        break

            if target_df is not None:
                tabular_payload = to_tabular_payload(target_df, dataset_name=step_name)
                save_tabular_artifact(target_df, self.run_id, step_name, self.environment)
                final_result.tabular_data = tabular_payload
                if is_polars_dataframe(final_result.data):
                    final_result.data = {
                        "__valiant_tabular__": True,
                        "rows": tabular_payload["total_rows"],
                        "columns": tabular_payload["total_columns"]
                    }
        except Exception as te:
            print(f"[Tabular Engine Notice] Failed to extract tabular data for {step_name}: {te}")

        await self._emit(RunEventType.STEP_FINISHED, step_name=step_name, data=final_result.model_dump())
        return final_result
