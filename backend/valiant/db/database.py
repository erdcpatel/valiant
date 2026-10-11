"""
Multi-environment database engine and query helpers.
Each environment (DEV, UAT, PROD) has its own isolated SQLite database file.
"""
import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import create_engine, desc, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from datetime import datetime

from .models import Base, WorkflowRunRecord, StepRunRecord, ScheduleRecord, WebhookRecord
from ..core.models import WorkflowResult
from ..core.environments import (
    get_allowed_environment_ids,
    get_default_environment,
    normalize_environment
)

_ENGINES: Dict[str, Engine] = {}
_SESSION_MAKERS: Dict[str, sessionmaker] = {}


def get_db_path(env: str = "dev") -> str:
    """Return file path for the environment's isolated SQLite database."""
    env = normalize_environment(env)
    data_dir = os.getenv("VALIANT_DATA_DIR", str(Path.cwd()))
    return os.path.join(data_dir, f"valiant_{env}.db")


def get_engine(env: str = "dev") -> Engine:
    """Retrieve or create an SQLAlchemy engine for the given environment."""
    env = normalize_environment(env)
    if env not in _ENGINES:
        db_path = Path(get_db_path(env)).resolve().as_posix()
        url = f"sqlite:///{db_path}"
        eng = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False
        )
        _ENGINES[env] = eng
        _SESSION_MAKERS[env] = sessionmaker(autocommit=False, autoflush=False, bind=eng)
        _run_migrations(eng)
    return _ENGINES[env]


def _run_migrations(eng: Engine):
    """Safely apply schema migrations to the given engine."""
    Base.metadata.create_all(bind=eng)
    migrations = [
        "ALTER TABLE workflow_runs ADD COLUMN environment TEXT DEFAULT 'dev'",
        "ALTER TABLE workflow_runs ADD COLUMN profile TEXT DEFAULT NULL",
        "ALTER TABLE workflow_runs ADD COLUMN triggered_by TEXT DEFAULT 'anonymous'",
        "ALTER TABLE workflow_runs ADD COLUMN parent_run_id TEXT DEFAULT NULL",
        "ALTER TABLE workflow_runs ADD COLUMN resumed_from_step TEXT DEFAULT NULL",
        "ALTER TABLE step_runs ADD COLUMN data_json TEXT DEFAULT 'null'",
        "ALTER TABLE step_runs ADD COLUMN reused BOOLEAN DEFAULT 0",
        "ALTER TABLE step_runs ADD COLUMN context_snapshot_json TEXT DEFAULT '{}'",
        "ALTER TABLE step_runs ADD COLUMN `order` INTEGER DEFAULT 100",
        "ALTER TABLE step_runs ADD COLUMN parallel_group TEXT DEFAULT NULL",
        "ALTER TABLE step_runs ADD COLUMN requires_json TEXT DEFAULT '[]'",
        "ALTER TABLE step_runs ADD COLUMN condition TEXT DEFAULT NULL",
        "ALTER TABLE step_runs ADD COLUMN tabular_data_json TEXT DEFAULT NULL",
    ]
    with eng.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass


def init_db(env: Optional[str] = None):
    """Initialize database tables for a specific environment or all allowed environments."""
    if env:
        get_engine(env)
    else:
        for e in get_allowed_environment_ids():
            get_engine(e)


@contextmanager
def get_session(env: str = "dev"):
    """Context manager for safe database session lifecycle targeting a specific environment."""
    eng = get_engine(env)
    sm = _SESSION_MAKERS[normalize_environment(env)]
    session: Session = sm()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def prune_run_history(max_keep: int = 50, days_retention: Optional[int] = None, env: str = "dev") -> int:
    """
    Prune older workflow runs in the specified environment to prevent database growth.
    Also executes SQLite VACUUM to physically reclaim disk space.
    """
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        all_runs = (
            session.query(WorkflowRunRecord.id)
            .order_by(desc(WorkflowRunRecord.started_at))
            .all()
        )
        if len(all_runs) <= max_keep:
            return 0

        runs_to_remove = all_runs[max_keep:]
        remove_ids = [r[0] for r in runs_to_remove]

        session.query(StepRunRecord).filter(StepRunRecord.run_id.in_(remove_ids)).delete(synchronize_session=False)
        deleted_count = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id.in_(remove_ids)).delete(synchronize_session=False)
        session.commit()

    # Reclaim SQLite disk pages
    try:
        eng = get_engine(env)
        with eng.connect() as conn:
            conn.execute(text("VACUUM"))
            conn.commit()
    except Exception as e:
        print(f"[DB Vacuum Info - {env}]: {e}")

    return deleted_count


def clear_all_runs(env: str = "dev") -> int:
    """Clear all workflow runs and steps in the specified environment database."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        session.query(StepRunRecord).delete(synchronize_session=False)
        deleted_count = session.query(WorkflowRunRecord).delete(synchronize_session=False)
        session.commit()
    try:
        eng = get_engine(env)
        with eng.connect() as conn:
            conn.execute(text("VACUUM"))
            conn.commit()
    except Exception:
        pass
    return deleted_count


def save_run_result(
    result: WorkflowResult,
    inputs: Optional[Dict[str, Any]] = None,
    triggered_by: str = "anonymous",
    env: str = "dev"
) -> WorkflowRunRecord:
    """Persist a completed or failed WorkflowResult to the environment's isolated SQLite DB."""
    env = normalize_environment(getattr(result, "environment", None) or env)
    init_db(env)
    inputs = inputs or {}

    with get_session(env) as session:
        existing = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == result.run_id).first()
        if existing:
            run_rec = existing
        else:
            run_rec = WorkflowRunRecord(id=result.run_id)
            session.add(run_rec)

        run_rec.workflow_name = result.workflow_name
        run_rec.status = result.status.value
        run_rec.success = result.success
        run_rec.parent_run_id = result.parent_run_id
        run_rec.resumed_from_step = result.resumed_from_step
        run_rec.total_steps = result.total_steps
        run_rec.executed_steps = result.executed_steps
        run_rec.successful_steps = result.successful_steps
        run_rec.failed_steps = result.failed_steps
        run_rec.skipped_steps = result.skipped_steps
        run_rec.total_time = result.total_time
        run_rec.started_at = result.started_at
        run_rec.completed_at = result.completed_at
        run_rec.triggered_by = triggered_by or "anonymous"
        run_rec.environment = env
        run_rec.profile = getattr(result, "profile", None)

        masked_inputs = {}
        for k, v in inputs.items():
            if any(secret in k.lower() for secret in ["password", "secret", "token", "key"]):
                masked_inputs[k] = "********"
            else:
                masked_inputs[k] = v
        run_rec.inputs_json = json.dumps(masked_inputs, default=str)
        run_rec.context_json = json.dumps(result.context, default=str)
        run_rec.error = result.error

        # Remove previous steps if re-saving
        session.query(StepRunRecord).filter(StepRunRecord.run_id == result.run_id).delete()

        # Add step run records with snapshot & reused status
        for s in result.results:
            step_rec = StepRunRecord(
                run_id=result.run_id,
                name=s.name,
                order=s.order,
                parallel_group=s.parallel_group,
                requires_json=json.dumps(s.requires or [], default=str),
                condition=s.condition,
                status=s.status.value,
                success=s.success,
                message=s.message,
                skipped=s.skipped,
                reused=s.reused,
                time_taken=s.time_taken,
                attempts=s.attempts,
                metrics_json=json.dumps(s.metrics, default=str),
                tags_json=json.dumps(s.tags, default=str),
                logs_json=json.dumps(s.logs, default=str),
                data_json=json.dumps(s.data if s.data is not None else None, default=str),
                context_before_json=json.dumps(s.context_before if getattr(s, "context_before", None) is not None else {}, default=str),
                context_snapshot_json=json.dumps(s.context_snapshot if s.context_snapshot is not None else {}, default=str),
                context_delta_json=json.dumps(s.context_delta.model_dump() if getattr(s, "context_delta", None) is not None else {}, default=str),
                lineage_json=json.dumps(s.lineage.model_dump() if getattr(s, "lineage", None) is not None else {}, default=str),
                error=s.error,
                tabular_data_json=json.dumps(s.tabular_data, default=str) if getattr(s, "tabular_data", None) else None,
                requires_approval=getattr(s, "requires_approval", False),
                approval_prompt=getattr(s, "approval_prompt", None),
                approved_by=getattr(s, "approved_by", None),
                approved_at=getattr(s, "approved_at", None),
                approval_notes=getattr(s, "approval_notes", None)
            )
            session.add(step_rec)

        session.commit()

        # Automated retention check
        try:
            total_count = session.query(WorkflowRunRecord).count()
            if total_count > 100:
                prune_run_history(max_keep=75, env=env)
        except Exception:
            pass

        return run_rec


def update_step_approval(
    run_id: str,
    step_name: str,
    approved: bool,
    approved_by: Optional[str] = None,
    notes: Optional[str] = None,
    env: str = "dev"
) -> bool:
    """Update approval status, operator, and timestamp for a suspended step."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        step = session.query(StepRunRecord).filter(
            StepRunRecord.run_id == run_id,
            StepRunRecord.name == step_name
        ).first()
        if not step:
            return False

        step.approved_by = approved_by or "operator"
        step.approved_at = datetime.utcnow().isoformat()
        step.approval_notes = notes
        step.status = "running" if approved else "rejected"
        step.success = approved
        if not approved:
            step.error = f"Rejected by operator: {notes or 'No reason provided'}"
            run_rec = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == run_id).first()
            if run_rec:
                run_rec.status = "failed"
                run_rec.error = f"Step '{step_name}' rejected by {approved_by or 'operator'}"
                run_rec.completed_at = datetime.utcnow().isoformat()
        session.commit()
        return True


def get_recent_runs(
    limit: int = 50,
    workflow_name: Optional[str] = None,
    triggered_by: Optional[str] = None,
    env: str = "dev"
) -> List[Dict[str, Any]]:
    """Retrieve run history ordered from newest to oldest for the specified environment."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        query = session.query(WorkflowRunRecord)
        if workflow_name:
            query = query.filter(WorkflowRunRecord.workflow_name == workflow_name)
        if triggered_by:
            query = query.filter(WorkflowRunRecord.triggered_by == triggered_by)
        runs = query.order_by(desc(WorkflowRunRecord.started_at)).limit(limit).all()
        return [r.to_dict() for r in runs]


def get_run_by_id(run_id: str, env: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch complete details of a specific run.
    If env is specified, checks that database.
    If not specified or not found, inspects all allowed environments seamlessly.
    """
    target_envs = [normalize_environment(env)] if env else get_allowed_environment_ids()
    for e in target_envs:
        init_db(e)
        with get_session(e) as session:
            run_rec = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == run_id).first()
            if run_rec:
                return run_rec.to_dict()

    # Fallback to any remaining allowed envs if specific env didn't match
    if env:
        for e in get_allowed_environment_ids():
            if e != env:
                init_db(e)
                with get_session(e) as session:
                    run_rec = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == run_id).first()
                    if run_rec:
                        return run_rec.to_dict()
    return None


def delete_run_by_id(run_id: str, env: Optional[str] = None) -> bool:
    """Delete a run from history across specified or all environments."""
    target_envs = [normalize_environment(env)] if env else get_allowed_environment_ids()
    for e in target_envs:
        init_db(e)
        with get_session(e) as session:
            run_rec = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == run_id).first()
            if run_rec:
                session.delete(run_rec)
                session.commit()
                return True
    return False


def save_initial_run_record(
    run_id: str,
    workflow_name: str,
    inputs: Dict[str, Any],
    triggered_by: str,
    initial_steps: List[Dict[str, Any]],
    parent_run_id: Optional[str] = None,
    resumed_from_step: Optional[str] = None,
    env: str = "dev",
    profile: Optional[str] = None
) -> WorkflowRunRecord:
    """Save an initial in-flight 'running' workflow record to SQLite for immediate client query discovery."""
    env = normalize_environment(env)
    init_db(env)
    inputs = inputs or {}
    with get_session(env) as session:
        existing = session.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == run_id).first()
        if not existing:
            run_rec = WorkflowRunRecord(
                id=run_id,
                workflow_name=workflow_name,
                status="running",
                success=False,
                parent_run_id=parent_run_id,
                resumed_from_step=resumed_from_step,
                total_steps=len(initial_steps),
                executed_steps=0,
                successful_steps=len([s for s in initial_steps if s.get("status") == "success"]),
                failed_steps=0,
                skipped_steps=0,
                total_time=0.0,
                started_at=datetime.utcnow().isoformat(),
                completed_at=None,
                triggered_by=triggered_by or "anonymous",
                environment=env,
                profile=profile,
                inputs_json=json.dumps(inputs),
                context_json=json.dumps({}),
                error=None,
            )
            session.add(run_rec)

            for s in initial_steps:
                step_rec = StepRunRecord(
                    run_id=run_id,
                    name=s["name"],
                    order=s.get("order", 100),
                    parallel_group=s.get("parallel_group"),
                    requires_json=json.dumps(s.get("requires", [])),
                    condition=s.get("condition"),
                    status=s.get("status", "pending"),
                    success=s.get("success", False),
                    message=s.get("message", "Pending execution"),
                    skipped=s.get("skipped", False),
                    reused=s.get("reused", False),
                    time_taken=s.get("time_taken", 0.0),
                    attempts=0,
                    metrics_json="{}",
                    tags_json=json.dumps(s.get("tags", [])),
                    logs_json="[]",
                    data_json="null",
                    context_snapshot_json=json.dumps(s.get("context_snapshot", {})),
                    error=None,
                )
                session.add(step_rec)

            session.commit()
            return run_rec
        return existing


# ---------------------------------------------------------------------------
# Schedules Query Helpers (Environment Partitioned)
# ---------------------------------------------------------------------------

def list_schedules(env: str = "dev") -> List[Dict[str, Any]]:
    """Retrieve all schedules configured in the environment."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        records = session.query(ScheduleRecord).order_by(desc(ScheduleRecord.created_at)).all()
        return [r.to_dict() for r in records]


def get_schedule(schedule_id: str, env: str = "dev") -> Optional[Dict[str, Any]]:
    """Fetch single schedule record by ID."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        rec = session.query(ScheduleRecord).filter(ScheduleRecord.id == schedule_id).first()
        return rec.to_dict() if rec else None


def create_schedule(data: Dict[str, Any], env: str = "dev") -> Dict[str, Any]:
    """Create and persist a new schedule."""
    import uuid
    env = normalize_environment(env)
    init_db(env)
    sched_id = data.get("id") or f"sched_{uuid.uuid4().hex[:8]}"
    inputs = data.get("inputs") or {}

    with get_session(env) as session:
        rec = ScheduleRecord(
            id=sched_id,
            name=data["name"],
            workflow_name=data["workflow_name"],
            cron_expression=data["cron_expression"],
            inputs_json=json.dumps(inputs),
            enabled=data.get("enabled", True),
            environment=env,
            next_run_at=data.get("next_run_at"),
            created_at=datetime.utcnow().isoformat()
        )
        session.add(rec)
        session.commit()
        return rec.to_dict()


def update_schedule(schedule_id: str, data: Dict[str, Any], env: str = "dev") -> Optional[Dict[str, Any]]:
    """Update fields of an existing schedule."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        rec = session.query(ScheduleRecord).filter(ScheduleRecord.id == schedule_id).first()
        if not rec:
            return None
        if "name" in data:
            rec.name = data["name"]
        if "workflow_name" in data:
            rec.workflow_name = data["workflow_name"]
        if "cron_expression" in data:
            rec.cron_expression = data["cron_expression"]
        if "inputs" in data:
            rec.inputs_json = json.dumps(data["inputs"])
        if "enabled" in data:
            rec.enabled = bool(data["enabled"])
        if "next_run_at" in data:
            rec.next_run_at = data["next_run_at"]
        session.commit()
        return rec.to_dict()


def delete_schedule(schedule_id: str, env: str = "dev") -> bool:
    """Delete a schedule."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        rec = session.query(ScheduleRecord).filter(ScheduleRecord.id == schedule_id).first()
        if rec:
            session.delete(rec)
            session.commit()
            return True
        return False


def get_due_schedules(env: str = "dev", now_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch active schedules whose next_run_at is <= now."""
    env = normalize_environment(env)
    init_db(env)
    now_iso = now_iso or datetime.utcnow().isoformat()
    with get_session(env) as session:
        records = session.query(ScheduleRecord).filter(
            ScheduleRecord.enabled == True,
            ScheduleRecord.next_run_at != None,
            ScheduleRecord.next_run_at <= now_iso
        ).all()
        return [r.to_dict() for r in records]


def update_schedule_after_run(
    schedule_id: str,
    run_id: str,
    status: str,
    next_run_at: Optional[str],
    env: str = "dev"
):
    """Update last run metadata on a schedule."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        rec = session.query(ScheduleRecord).filter(ScheduleRecord.id == schedule_id).first()
        if rec:
            rec.last_run_at = datetime.utcnow().isoformat()
            rec.last_run_id = run_id
            rec.last_status = status
            if next_run_at:
                rec.next_run_at = next_run_at
            session.commit()


# ---------------------------------------------------------------------------
# Webhooks Query Helpers (Environment Partitioned)
# ---------------------------------------------------------------------------

def list_webhooks(env: str = "dev") -> List[Dict[str, Any]]:
    """Retrieve all webhooks configured in the environment."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        records = session.query(WebhookRecord).order_by(desc(WebhookRecord.created_at)).all()
        return [r.to_dict() for r in records]


def get_webhook(webhook_id: str, env: str = "dev") -> Optional[Dict[str, Any]]:
    """Fetch single webhook by ID."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        rec = session.query(WebhookRecord).filter(WebhookRecord.id == webhook_id).first()
        return rec.to_dict() if rec else None


def get_webhook_by_token(token: str, env: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Search for a webhook by token. If env is not specified, search across all allowed envs.
    """
    envs = [normalize_environment(env)] if env else get_allowed_environment_ids()
    for e in envs:
        try:
            init_db(e)
            with get_session(e) as session:
                rec = session.query(WebhookRecord).filter(WebhookRecord.token == token).first()
                if rec:
                    return rec.to_dict()
        except Exception:
            continue
    return None


def create_webhook(data: Dict[str, Any], env: str = "dev") -> Dict[str, Any]:
    """Create and persist a new inbound webhook."""
    import uuid
    env = normalize_environment(env)
    init_db(env)
    hook_id = data.get("id") or f"hook_{uuid.uuid4().hex[:8]}"
    token = data.get("token") or f"wh_{uuid.uuid4().hex[:16]}"
    mapping = data.get("parameter_mapping") or {}

    with get_session(env) as session:
        rec = WebhookRecord(
            id=hook_id,
            name=data["name"],
            workflow_name=data["workflow_name"],
            token=token,
            environment=env,
            enabled=data.get("enabled", True),
            secret_header=data.get("secret_header"),
            parameter_mapping_json=json.dumps(mapping),
            trigger_count=0,
            created_at=datetime.utcnow().isoformat()
        )
        session.add(rec)
        session.commit()
        return rec.to_dict()


def update_webhook(webhook_id: str, data: Dict[str, Any], env: str = "dev") -> Optional[Dict[str, Any]]:
    """Update webhook properties."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        rec = session.query(WebhookRecord).filter(WebhookRecord.id == webhook_id).first()
        if not rec:
            return None
        if "name" in data:
            rec.name = data["name"]
        if "workflow_name" in data:
            rec.workflow_name = data["workflow_name"]
        if "enabled" in data:
            rec.enabled = bool(data["enabled"])
        if "secret_header" in data:
            rec.secret_header = data["secret_header"]
        if "parameter_mapping" in data:
            rec.parameter_mapping_json = json.dumps(data["parameter_mapping"])
        session.commit()
        return rec.to_dict()


def delete_webhook(webhook_id: str, env: str = "dev") -> bool:
    """Delete a webhook."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        rec = session.query(WebhookRecord).filter(WebhookRecord.id == webhook_id).first()
        if rec:
            session.delete(rec)
            session.commit()
            return True
        return False


def record_webhook_trigger(webhook_id: str, env: str = "dev"):
    """Increment trigger count and update timestamp."""
    env = normalize_environment(env)
    init_db(env)
    with get_session(env) as session:
        rec = session.query(WebhookRecord).filter(WebhookRecord.id == webhook_id).first()
        if rec:
            rec.trigger_count = (rec.trigger_count or 0) + 1
            rec.last_triggered_at = datetime.utcnow().isoformat()
            session.commit()
