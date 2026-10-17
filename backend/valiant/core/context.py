"""
Context management for workflow execution with secret masking, lineage telemetry,
cross-platform subprocess execution (context.exec), and async deployment polling (context.poll_until).
"""
import os
import shlex
import shutil
import subprocess
import asyncio
import inspect
import time
import urllib.request
import json
from typing import Any, Dict, Set, Optional, Iterator, List, Union, Callable, Tuple
from copy import deepcopy

from .models import CommandResult, RunEventType
from .logging import RunLogManager


class ScopedStepContext:
    """
    A step-scoped view of WorkflowContext that isolates read/write/delete telemetry
    per step, ensuring accurate data lineage even during concurrent parallel execution.
    """

    def __init__(self, parent: "WorkflowContext", step_name: str):
        self._parent = parent
        self.step_name = step_name
        self.reads: Set[str] = set()
        self.writes: Set[str] = set()
        self.deletes: Set[str] = set()

    def get_telemetry(self) -> Dict[str, List[str]]:
        return {
            "reads": sorted(list(self.reads)),
            "writes": sorted(list(self.writes)),
            "deletes": sorted(list(self.deletes)),
        }

    def mark_sensitive(self, key: str) -> None:
        self._parent.mark_sensitive(key)

    def get(self, key: str, default: Any = None) -> Any:
        self.reads.add(key)
        return self._parent.get(key, default)

    def set(self, key: str, value: Any, sensitive: bool = False) -> None:
        self.writes.add(key)
        self._parent.set(key, value, sensitive=sensitive)

    def __getitem__(self, key: str) -> Any:
        self.reads.add(key)
        return self._parent[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.writes.add(key)
        self._parent[key] = value

    def __delitem__(self, key: str) -> None:
        self.deletes.add(key)
        del self._parent[key]

    def pop(self, key: str, *args: Any) -> Any:
        self.deletes.add(key)
        return self._parent.pop(key, *args)

    def __contains__(self, key: str) -> bool:
        self.reads.add(key)
        return key in self._parent

    def __iter__(self) -> Iterator[str]:
        return iter(self._parent)

    def __len__(self) -> int:
        return len(self._parent)

    def keys(self):
        return self._parent.keys()

    def values(self):
        return self._parent.values()

    def items(self):
        return self._parent.items()

    def update(self, other: Dict[str, Any]) -> None:
        if other:
            self.writes.update(other.keys())
        self._parent.update(other)

    def to_dict(self, mask_secrets: bool = True) -> Dict[str, Any]:
        return self._parent.to_dict(mask_secrets=mask_secrets)

    def log(self, message: str, stream: str = "stdout") -> None:
        """Log a line associated with this step, write to run log file, and stream via WebSocket."""
        self._parent.log(message, step_name=self.step_name, stream=stream)

    async def exec(
        self,
        command: Union[List[str], str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        stream_logs: bool = True
    ) -> CommandResult:
        """Execute a cross-platform command asynchronously in the context of this step."""
        return await self._parent.exec(
            command=command,
            cwd=cwd,
            env=env,
            timeout=timeout,
            stream_logs=stream_logs,
            step_name=self.step_name
        )

    async def poll_until(
        self,
        check_target: Union[Callable, str],
        predicate: Optional[Callable[[Any], bool]] = None,
        timeout: float = 600.0,
        interval: float = 10.0,
        description: str = "Polling...",
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Any]:
        """Poll a target function or HTTP URL until predicate passes or timeout occurs."""
        return await self._parent.poll_until(
            check_target=check_target,
            predicate=predicate,
            timeout=timeout,
            interval=interval,
            description=description,
            step_name=self.step_name,
            headers=headers
        )


class WorkflowContext:
    """
    Isolated execution context passed between workflow steps.
    Provides dictionary-like access, automatic sensitive data redacting,
    step-scoped telemetry for live data lineage, cross-platform subprocess runner,
    and async deployment polling.
    """

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None, sensitive_keys: Optional[Set[str]] = None):
        self._data: Dict[str, Any] = dict(initial_data or {})
        self._sensitive_keys: Set[str] = set(sensitive_keys or set())
        self._runner: Optional[Any] = None
        self._run_id: str = "run_default"
        self._environment: str = "dev"

    def bind_runner(self, runner: Any) -> None:
        """Bind active WorkflowRunner instance to enable live streaming and process management."""
        self._runner = runner
        self._run_id = getattr(runner, "run_id", "run_default")
        self._environment = getattr(runner, "environment", "dev")

    def scoped(self, step_name: str) -> ScopedStepContext:
        """Create a step-isolated context view for per-step access tracking."""
        return ScopedStepContext(self, step_name)

    def mark_sensitive(self, key: str) -> None:
        """Mark a context key as sensitive (will be redacted in dumps)."""
        self._sensitive_keys.add(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, sensitive: bool = False) -> None:
        self._data[key] = value
        if sensitive:
            self._sensitive_keys.add(key)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def pop(self, key: str, *args: Any) -> Any:
        return self._data.pop(key, *args)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def update(self, other: Dict[str, Any]) -> None:
        self._data.update(other)

    def to_dict(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Convert to standard dict, optionally redacting sensitive values."""
        result = {}
        for k, v in self._data.items():
            is_secret = (
                k in self._sensitive_keys or
                any(secret_word in k.lower() for secret_word in ["password", "secret", "token", "api_key", "auth_token"])
            )
            if mask_secrets and is_secret and v is not None:
                result[k] = "********"
            else:
                try:
                    from .tabular import is_polars_dataframe, to_tabular_payload
                    if is_polars_dataframe(v):
                        result[k] = to_tabular_payload(v, dataset_name=k)
                    else:
                        result[k] = deepcopy(v)
                except Exception:
                    result[k] = str(v)
        return result

    def log(self, message: str, step_name: Optional[str] = None, stream: str = "stdout") -> None:
        """Write line to disk run log and emit real-time STEP_LOG WebSocket event."""
        # 1. Synchronously append to disk log file
        RunLogManager.append_line(
            run_id=self._run_id,
            line=message,
            step_name=step_name,
            stream=stream,
            env=self._environment
        )

        # 2. Asynchronously emit to runner if active
        if self._runner and hasattr(self._runner, "_emit"):
            event_data = {
                "line": f"[{step_name}] {message}" if step_name else message,
                "step_name": step_name,
                "stream": stream,
                "timestamp": time.time()
            }
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._runner._emit(RunEventType.STEP_LOG, step_name=step_name, data=event_data))
            except RuntimeError:
                pass

    async def exec(
        self,
        command: Union[List[str], str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        stream_logs: bool = True,
        step_name: Optional[str] = None
    ) -> CommandResult:
        """
        Execute an external shell/binary command asynchronously with streaming output,
        cross-platform resolution (Windows .cmd/.bat), and active process tracking.
        """
        if isinstance(command, str):
            cmd_list = shlex.split(command, posix=(os.name != "nt"))
        else:
            cmd_list = [str(c) for c in command]

        if not cmd_list:
            return CommandResult(
                command=[],
                exit_code=-1,
                stdout="",
                stderr="Command list cannot be empty",
                duration=0.0,
                success=False
            )

        # Cross-platform executable path resolution (handles mvn -> mvn.cmd on Windows)
        executable = shutil.which(cmd_list[0])
        if executable:
            cmd_list[0] = executable

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        extra_kwargs: Dict[str, Any] = {}
        if os.name == "nt":
            extra_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            extra_kwargs["preexec_fn"] = os.setsid

        start_time = time.time()
        self.log(f"[EXEC] Running: {' '.join(cmd_list)} (cwd: {cwd or os.getcwd()})", step_name=step_name)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_list,
                cwd=cwd,
                env=merged_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **extra_kwargs
            )
        except Exception as e:
            err_msg = f"Failed to spawn process '{cmd_list[0]}': {e}"
            self.log(f"[EXEC ERROR] {err_msg}", step_name=step_name, stream="stderr")
            return CommandResult(
                command=cmd_list,
                exit_code=-1,
                stdout="",
                stderr=err_msg,
                duration=round(time.time() - start_time, 3),
                success=False
            )

        # Register active process with runner for responsive abort/kill
        if self._runner and hasattr(self._runner, "register_process"):
            self._runner.register_process(proc)

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []

        async def read_stream(stream: asyncio.StreamReader, is_stderr: bool = False):
            while True:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break
                line_str = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")
                if is_stderr:
                    stderr_lines.append(line_str)
                    if stream_logs:
                        self.log(line_str, step_name=step_name, stream="stderr")
                else:
                    stdout_lines.append(line_str)
                    if stream_logs:
                        self.log(line_str, step_name=step_name, stream="stdout")

        try:
            if timeout:
                await asyncio.wait_for(
                    asyncio.gather(read_stream(proc.stdout, False), read_stream(proc.stderr, True)),
                    timeout=timeout
                )
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            else:
                await asyncio.gather(read_stream(proc.stdout, False), read_stream(proc.stderr, True))
                await proc.wait()
        except asyncio.TimeoutError:
            self.log(f"[TIMEOUT] Process timed out after {timeout}s - terminating", step_name=step_name, stream="stderr")
            try:
                if self._runner and hasattr(self._runner, "kill_process"):
                    self._runner.kill_process(proc)
                else:
                    proc.kill()
                await proc.wait()
            except Exception:
                pass
            return CommandResult(
                command=cmd_list,
                exit_code=-1,
                stdout="\n".join(stdout_lines),
                stderr=f"Timed out after {timeout}s\n" + "\n".join(stderr_lines),
                duration=round(time.time() - start_time, 3),
                success=False,
                pid=proc.pid
            )
        finally:
            if self._runner and hasattr(self._runner, "unregister_process"):
                self._runner.unregister_process(proc)

        duration = round(time.time() - start_time, 3)
        exit_code = proc.returncode if proc.returncode is not None else -1
        is_success = (exit_code == 0)

        status_tag = "SUCCESS" if is_success else f"FAILED (exit {exit_code})"
        self.log(f"[EXEC] Completed in {duration}s [{status_tag}]", step_name=step_name)

        return CommandResult(
            command=cmd_list,
            exit_code=exit_code,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines),
            duration=duration,
            success=is_success,
            pid=proc.pid
        )

    async def poll_until(
        self,
        check_target: Union[Callable, str],
        predicate: Optional[Callable[[Any], bool]] = None,
        timeout: float = 600.0,
        interval: float = 10.0,
        description: str = "Polling...",
        step_name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Any]:
        """
        Poll a target URL or async/sync function until the predicate returns True,
        emitting live heartbeat logs and respecting runner cancellation.
        """
        start_time = time.time()
        attempt = 0
        last_result: Any = None

        self.log(f"Starting poll: {description} (Timeout: {timeout}s, Interval: {interval}s)", step_name=step_name)

        while (time.time() - start_time) < timeout:
            if self._runner and getattr(self._runner, "cancelled", False):
                self.log(f"⚠ Polling aborted: Run cancelled by operator", step_name=step_name)
                return False, "Cancelled"

            attempt += 1
            elapsed = time.time() - start_time

            try:
                if isinstance(check_target, str):
                    # HTTP endpoint check
                    def _do_http_check():
                        req = urllib.request.Request(
                            check_target,
                            headers=headers or {"Accept": "application/json", "User-Agent": "Valiant-Runner"}
                        )
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            body = resp.read().decode("utf-8")
                            try:
                                return json.loads(body)
                            except Exception:
                                return body

                    last_result = await asyncio.to_thread(_do_http_check)
                elif callable(check_target):
                    if inspect.iscoroutinefunction(check_target):
                        last_result = await check_target()
                    else:
                        last_result = check_target()
                else:
                    last_result = check_target

                # Evaluate predicate
                passed = predicate(last_result) if predicate else bool(last_result)
                if passed:
                    self.log(
                        f"✔ {description} verified on attempt {attempt} (Elapsed: {round(elapsed, 1)}s)",
                        step_name=step_name
                    )
                    return True, last_result
            except Exception as e:
                last_result = str(e)

            self.log(
                f"⏳ {description} (Attempt {attempt}, elapsed {round(elapsed, 0)}s/{timeout:.0f}s)",
                step_name=step_name
            )

            # Sleep in 1-second slices so cancellation triggers immediately
            sleep_slices = max(1, int(interval))
            for _ in range(sleep_slices):
                if self._runner and getattr(self._runner, "cancelled", False):
                    self.log(f"⚠ Polling aborted: Run cancelled by operator", step_name=step_name)
                    return False, "Cancelled"
                await asyncio.sleep(1.0)

        elapsed = time.time() - start_time
        self.log(
            f"✖ Polling timed out after {round(elapsed, 1)}s ({attempt} attempts): {description}",
            step_name=step_name,
            stream="stderr"
        )
        return False, last_result
