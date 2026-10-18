"""
In-process asynchronous background scheduler for periodic cron workflows.
Runs self-contained within FastAPI async lifecycle with zero external broker dependencies.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from .registry import registry
from .runner import WorkflowRunner
from .cron_utils import compute_next_run_iso, validate_cron_expression
from ..db.database import (
    get_due_schedules,
    get_schedule,
    update_schedule_after_run,
    update_schedule,
    save_run_result,
    normalize_environment,
    get_allowed_environment_ids,
)

logger = logging.getLogger("valiant.scheduler")


class AsyncScheduler:
    """
    Lightweight, partition-aware async scheduler that periodically evaluates
    registered schedules across DEV, UAT, and PROD databases.
    """

    def __init__(self, check_interval_seconds: int = 15):
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        """Start the background scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Valiant AsyncScheduler started (interval: %ss)", self.check_interval_seconds)

    async def stop(self):
        """Gracefully stop the background scheduler loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Valiant AsyncScheduler stopped")

    async def _scheduler_loop(self):
        """Main periodic polling loop."""
        # Initial brief wait on server startup to allow full DB initialization
        await asyncio.sleep(2)

        while self._running:
            try:
                await self._evaluate_due_schedules()
            except Exception as e:
                logger.error("Error during scheduler loop tick: %s", e, exc_info=True)

            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break

    async def _evaluate_due_schedules(self):
        """Scan active schedules across allowed environments and fire due tasks."""
        envs = get_allowed_environment_ids()
        now_iso = datetime.utcnow().isoformat()

        for env in envs:
            try:
                due_list = get_due_schedules(env=env, now_iso=now_iso)
                for sched in due_list:
                    # Double-check enabled status
                    if not sched.get("enabled"):
                        continue

                    # Compute next execution time immediately to avoid double-firing
                    cron_expr = sched.get("cron_expression", "")
                    next_run_iso = compute_next_run_iso(cron_expr)
                    update_schedule(sched["id"], {"next_run_at": next_run_iso}, env=env)

                    # Trigger workflow asynchronously
                    asyncio.create_task(self._execute_scheduled_workflow(sched, env))
            except Exception as env_err:
                logger.error("Failed to check due schedules for env '%s': %s", env, env_err)

    async def _execute_scheduled_workflow(self, schedule: Dict[str, Any], env: str) -> Optional[str]:
        """Instantiate workflow, execute via WorkflowRunner, and persist result."""
        sched_id = schedule["id"]
        sched_name = schedule["name"]
        wf_name = schedule["workflow_name"]
        inputs = schedule.get("inputs") or {}

        workflow_instance = registry.get_instance(wf_name)
        if not workflow_instance:
            logger.warning("Scheduled workflow '%s' not found in registry (schedule: %s)", wf_name, sched_id)
            update_schedule_after_run(sched_id, "unknown", "failed", None, env=env)
            return None
        runner = WorkflowRunner(
            workflow=workflow_instance,
            environment=env,
            profile=env,
            stop_on_failure=True
        )

        triggered_by = f"cron: {sched_name}"
        logger.info("Triggering scheduled run %s for '%s' in %s", runner.run_id, wf_name, env)

        try:
            result = await runner.run(inputs)
            save_run_result(result, inputs, triggered_by=triggered_by, env=env)
            status = "completed" if result.success else "failed"
            update_schedule_after_run(sched_id, runner.run_id, status, None, env=env)
            return runner.run_id
        except Exception as e:
            logger.error("Execution error in scheduled run %s: %s", runner.run_id, e, exc_info=True)
            update_schedule_after_run(sched_id, runner.run_id, "failed", None, env=env)
            return runner.run_id

    async def trigger_now(self, schedule_id: str, env: str = "dev") -> Optional[str]:
        """Manually trigger a schedule immediately out-of-band."""
        sched = get_schedule(schedule_id, env=env)
        if not sched:
            return None
        return await self._execute_scheduled_workflow(sched, env=env)


# Global singleton scheduler instance
scheduler = AsyncScheduler(check_interval_seconds=15)
