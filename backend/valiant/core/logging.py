"""
Valiant Run Log Manager: Synchronous, cross-platform file logger that writes
untruncated raw execution logs to .valiant/logs/{env}/{run_id}.log.
"""
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json

LOGS_BASE_DIR = os.environ.get("VALIANT_LOGS_DIR", ".valiant/logs")
_LOG_LOCKS: Dict[str, threading.Lock] = {}
_GLOBAL_LOCK = threading.Lock()


def _get_lock(run_id: str) -> threading.Lock:
    with _GLOBAL_LOCK:
        if run_id not in _LOG_LOCKS:
            _LOG_LOCKS[run_id] = threading.Lock()
        return _LOG_LOCKS[run_id]


def get_log_path(run_id: str, env: str = "dev") -> Path:
    """Return the absolute Path for a run's .log file."""
    env_clean = (env or "dev").lower().strip()
    folder = Path(LOGS_BASE_DIR) / env_clean
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{run_id}.log"


class RunLogManager:
    """Manages dedicated per-run .log files on the local filesystem."""

    @staticmethod
    def get_path(run_id: str, env: str = "dev") -> Path:
        return get_log_path(run_id, env)

    @staticmethod
    def init_run_log(
        run_id: str,
        workflow_name: str,
        env: str = "dev",
        inputs: Optional[Dict[str, Any]] = None,
        triggered_by: str = "system",
        started_at: Optional[str] = None
    ) -> Path:
        """Create and initialize a run log file with metadata header."""
        path = get_log_path(run_id, env)
        started_iso = started_at or datetime.utcnow().isoformat()
        lock = _get_lock(run_id)

        clean_inputs = {}
        for k, v in (inputs or {}).items():
            if any(s in k.lower() for s in ["password", "secret", "token", "key"]):
                clean_inputs[k] = "******"
            else:
                clean_inputs[k] = v

        header = [
            "=" * 80,
            f"VALIANT EXECUTION LOG: {run_id}",
            f"Workflow     : {workflow_name}",
            f"Environment  : {env.upper()}",
            f"Triggered By : {triggered_by}",
            f"Started At   : {started_iso} UTC",
            f"Inputs       : {json.dumps(clean_inputs, default=str)}",
            "=" * 80,
            ""
        ]

        with lock:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(header) + "\n")
        return path

    @staticmethod
    def append_step_start(run_id: str, step_name: str, order: int = 100, env: str = "dev") -> None:
        """Record step entry boundary."""
        now = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        line = f"\n>>> [{now}] [STEP_START] Step {order}: {step_name}\n"
        path = get_log_path(run_id, env)
        lock = _get_lock(run_id)
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)

    @staticmethod
    def append_step_end(
        run_id: str,
        step_name: str,
        status: str,
        duration: float = 0.0,
        message: Optional[str] = None,
        env: str = "dev"
    ) -> None:
        """Record step completion boundary."""
        now = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        msg_part = f" - {message}" if message else ""
        line = f"<<< [{now}] [STEP_END] {step_name} [{status.upper()}] ({duration:.3f}s){msg_part}\n"
        path = get_log_path(run_id, env)
        lock = _get_lock(run_id)
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)

    @staticmethod
    def append_line(
        run_id: str,
        line: str,
        step_name: Optional[str] = None,
        stream: str = "stdout",
        env: str = "dev"
    ) -> None:
        """Append a single log or command output line."""
        now = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        prefix = f"[{now}]"
        if step_name:
            prefix += f" [{step_name}]"
        if stream == "stderr":
            prefix += " [STDERR]"
        
        formatted = f"{prefix} {line}\n"
        path = get_log_path(run_id, env)
        lock = _get_lock(run_id)
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(formatted)

    @staticmethod
    def finalize_run_log(
        run_id: str,
        status: str,
        duration: float,
        total_steps: int = 0,
        successful_steps: int = 0,
        failed_steps: int = 0,
        env: str = "dev"
    ) -> None:
        """Write summary footer banner."""
        now = datetime.utcnow().isoformat()
        footer = [
            "",
            "=" * 80,
            f"RUN FINISHED: {status.upper()}",
            f"Total Duration   : {duration:.3f}s",
            f"Steps Completed  : {successful_steps}/{total_steps} passed ({failed_steps} failed)",
            f"Completed At     : {now} UTC",
            "=" * 80,
            ""
        ]
        path = get_log_path(run_id, env)
        lock = _get_lock(run_id)
        with lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n".join(footer) + "\n")

    @staticmethod
    def read_log_content(run_id: str, env: str = "dev") -> str:
        """Read the full raw text content of a run log file."""
        path = get_log_path(run_id, env)
        if not path.exists():
            return f"[Log file not found at {path}]"
        lock = _get_lock(run_id)
        with lock:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
