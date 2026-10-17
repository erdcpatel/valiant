"""
Tests for Valiant Desktop Automation Engine:
- Async Subprocess Runner (context.exec) with cross-platform resolution
- Live WebSocket & File Log Streaming
- RunLogManager (.valiant/logs/{env}/{run_id}.log)
- Process Tree Cancellation & Abort
- Async Polling Helper (context.poll_until)
"""
import pytest
import asyncio
import os
import sys
import time
from pathlib import Path

from backend.valiant.core.context import WorkflowContext
from backend.valiant.core.runner import WorkflowRunner
from backend.valiant.core.workflow import Workflow, step
from backend.valiant.core.models import RunEventType, StepStatus, StepResult
from backend.valiant.core.logging import RunLogManager, get_log_path


@pytest.mark.anyio
async def test_context_exec_basic():
    """Verify context.exec runs commands and captures exit_code, stdout, and duration."""
    ctx = WorkflowContext()
    cmd = [sys.executable, "-c", "import sys; sys.stdout.write('hello stdout\\n'); sys.stderr.write('hello stderr\\n')"]
    result = await ctx.exec(cmd, stream_logs=False)

    assert result.success is True
    assert result.exit_code == 0
    assert "hello stdout" in result.stdout
    assert "hello stderr" in result.stderr
    assert result.duration >= 0.0


@pytest.mark.anyio
async def test_context_exec_timeout():
    """Verify context.exec terminates a hanging process when timeout expires."""
    ctx = WorkflowContext()
    cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
    result = await ctx.exec(cmd, timeout=1.0)

    assert result.success is False
    assert result.exit_code == -1
    assert "Timed out" in result.stderr


@pytest.mark.anyio
async def test_run_log_manager(tmp_path, monkeypatch):
    """Verify RunLogManager writes and reads .valiant/logs/{env}/{run_id}.log."""
    monkeypatch.setenv("VALIANT_LOGS_DIR", str(tmp_path / "logs"))
    run_id = "test_run_123"
    env = "dev"

    log_file = RunLogManager.init_run_log(
        run_id=run_id,
        workflow_name="demo_wf",
        env=env,
        inputs={"param1": "value1", "token": "secret123"},
        triggered_by="tester"
    )

    assert log_file.exists()
    RunLogManager.append_step_start(run_id, "Compile Step", order=1, env=env)
    RunLogManager.append_line(run_id, "[INFO] Compiling...", step_name="Compile Step", env=env)
    RunLogManager.append_step_end(run_id, "Compile Step", status="success", duration=1.23, env=env)
    RunLogManager.finalize_run_log(run_id, status="completed", duration=2.5, total_steps=1, successful_steps=1, failed_steps=0, env=env)

    content = RunLogManager.read_log_content(run_id, env=env)
    assert "VALIANT EXECUTION LOG: test_run_123" in content
    assert "demo_wf" in content
    assert "******" in content  # Masked secret
    assert "[STEP_START] Step 1: Compile Step" in content
    assert "[INFO] Compiling..." in content
    assert "[STEP_END] Compile Step [SUCCESS]" in content
    assert "RUN FINISHED: COMPLETED" in content


@pytest.mark.anyio
async def test_context_poll_until_success():
    """Verify context.poll_until succeeds after matching predicate."""
    ctx = WorkflowContext()
    counter = 0

    async def mock_endpoint():
        nonlocal counter
        counter += 1
        return {"status": "ready" if counter >= 2 else "pending"}

    ok, res = await ctx.poll_until(
        check_target=mock_endpoint,
        predicate=lambda r: r.get("status") == "ready",
        timeout=10,
        interval=1,
        description="Waiting for mock deployment"
    )

    assert ok is True
    assert res == {"status": "ready"}
    assert counter == 2


@pytest.mark.anyio
async def test_context_poll_until_timeout():
    """Verify context.poll_until returns False upon timeout."""
    ctx = WorkflowContext()

    ok, res = await ctx.poll_until(
        check_target=lambda: {"status": "never_ready"},
        predicate=lambda r: r.get("status") == "ready",
        timeout=1.5,
        interval=1,
        description="Waiting for impossible state"
    )

    assert ok is False
    assert res == {"status": "never_ready"}


class ProcessKillWorkflow(Workflow):
    workflow_id = "process_kill_test"

    @step(order=1)
    async def long_step(self, context: WorkflowContext) -> StepResult:
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        res = await context.exec(cmd)
        return self.success("Finished", data=res)


@pytest.mark.anyio
async def test_runner_process_cancellation():
    """Verify runner.cancel() terminates active child processes immediately."""
    wf = ProcessKillWorkflow()
    runner = WorkflowRunner(workflow=wf, run_id="run_cancel_test", environment="dev")

    # Run in background task
    run_task = asyncio.create_task(runner.run())

    # Wait for process to spawn
    await asyncio.sleep(1.0)
    assert len(runner._active_processes) == 1

    # Call cancel
    t0 = time.time()
    runner.cancel()

    res = await run_task
    dur = time.time() - t0

    assert dur < 3.0  # Must terminate within seconds, not wait for 30s sleep!
    assert runner.cancelled is True
    assert res.status == "cancelled"

    # Give anyio / asyncio loop time to flush transport pipe callbacks
    await asyncio.sleep(0.1)
