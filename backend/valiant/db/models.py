"""
SQLAlchemy ORM models for workflow execution history.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
import json

Base = declarative_base()


class WorkflowRunRecord(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(64), primary_key=True)
    workflow_name = Column(String(128), nullable=False, index=True)
    status = Column(String(32), default="pending", index=True)
    success = Column(Boolean, default=False)
    total_steps = Column(Integer, default=0)
    executed_steps = Column(Integer, default=0)
    successful_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    skipped_steps = Column(Integer, default=0)
    total_time = Column(Float, default=0.0)
    started_at = Column(String(64), default=lambda: datetime.utcnow().isoformat())
    completed_at = Column(String(64), nullable=True)
    triggered_by = Column(String(128), default="anonymous", index=True)
    parent_run_id = Column(String(64), nullable=True, index=True)
    resumed_from_step = Column(String(128), nullable=True)
    inputs_json = Column(Text, default="{}")
    context_json = Column(Text, default="{}")
    environment = Column(String(32), default="dev", index=True)
    profile = Column(String(64), nullable=True)
    error = Column(Text, nullable=True)

    steps = relationship("StepRunRecord", back_populates="run", cascade="all, delete-orphan", order_by="StepRunRecord.id")

    def to_dict(self):
        return {
            "id": self.id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "success": self.success,
            "parent_run_id": self.parent_run_id,
            "resumed_from_step": self.resumed_from_step,
            "total_steps": self.total_steps,
            "executed_steps": self.executed_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "total_time": self.total_time,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "triggered_by": self.triggered_by or "anonymous",
            "environment": self.environment or "dev",
            "profile": self.profile,
            "inputs": json.loads(self.inputs_json or "{}"),
            "context": json.loads(self.context_json or "{}"),
            "error": self.error,
            "steps": [s.to_dict() for s in self.steps]
        }


class StepRunRecord(Base):
    __tablename__ = "step_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    order = Column(Integer, default=100)
    parallel_group = Column(String(100), nullable=True)
    requires_json = Column(Text, default="[]")
    condition = Column(String(100), nullable=True)
    status = Column(String(32), default="pending")
    success = Column(Boolean, default=False)
    message = Column(Text, default="")
    skipped = Column(Boolean, default=False)
    reused = Column(Boolean, default=False)
    context_before_json = Column(Text, default="{}")
    context_snapshot_json = Column(Text, default="{}")
    context_delta_json = Column(Text, default="{}")
    lineage_json = Column(Text, default="{}")
    time_taken = Column(Float, default=0.0)
    attempts = Column(Integer, default=1)
    metrics_json = Column(Text, default="{}")
    tags_json = Column(Text, default="[]")
    logs_json = Column(Text, default="[]")
    data_json = Column(Text, default="null")
    error = Column(Text, nullable=True)
    tabular_data_json = Column(Text, nullable=True)
    requires_approval = Column(Boolean, default=False)
    approval_prompt = Column(Text, nullable=True)
    approved_by = Column(String(128), nullable=True)
    approved_at = Column(String(64), nullable=True)
    approval_notes = Column(Text, nullable=True)

    run = relationship("WorkflowRunRecord", back_populates="steps")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "order": self.order or 100,
            "parallel_group": self.parallel_group,
            "requires": json.loads(self.requires_json or "[]"),
            "condition": self.condition,
            "status": self.status,
            "success": self.success,
            "message": self.message,
            "skipped": self.skipped,
            "reused": bool(self.reused),
            "requires_approval": bool(self.requires_approval),
            "approval_prompt": self.approval_prompt,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "approval_notes": self.approval_notes,
            "tabular_data": json.loads(self.tabular_data_json) if self.tabular_data_json else None,
            "context_before": json.loads(self.context_before_json or "{}"),
            "context_snapshot": json.loads(self.context_snapshot_json or "{}"),
            "context_delta": json.loads(self.context_delta_json or "{}"),
            "lineage": json.loads(self.lineage_json or "{}"),
            "time_taken": self.time_taken,
            "attempts": self.attempts,
            "metrics": json.loads(self.metrics_json or "{}"),
            "tags": json.loads(self.tags_json or "[]"),
            "logs": json.loads(self.logs_json or "[]"),
            "data": json.loads(self.data_json or "null"),
            "error": self.error
        }


class ScheduleRecord(Base):
    __tablename__ = "schedules"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    workflow_name = Column(String(128), nullable=False, index=True)
    cron_expression = Column(String(64), nullable=False)
    inputs_json = Column(Text, default="{}")
    enabled = Column(Boolean, default=True)
    environment = Column(String(32), default="dev", index=True)
    last_run_at = Column(String(64), nullable=True)
    last_run_id = Column(String(64), nullable=True)
    last_status = Column(String(32), nullable=True)
    next_run_at = Column(String(64), nullable=True)
    created_at = Column(String(64), default=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "workflow_name": self.workflow_name,
            "cron_expression": self.cron_expression,
            "inputs": json.loads(self.inputs_json or "{}"),
            "enabled": bool(self.enabled),
            "environment": self.environment or "dev",
            "last_run_at": self.last_run_at,
            "last_run_id": self.last_run_id,
            "last_status": self.last_status,
            "next_run_at": self.next_run_at,
            "created_at": self.created_at,
        }


class WebhookRecord(Base):
    __tablename__ = "webhooks"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    workflow_name = Column(String(128), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    environment = Column(String(32), default="dev", index=True)
    enabled = Column(Boolean, default=True)
    secret_header = Column(String(128), nullable=True)
    parameter_mapping_json = Column(Text, default="{}")
    trigger_count = Column(Integer, default=0)
    last_triggered_at = Column(String(64), nullable=True)
    created_at = Column(String(64), default=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "workflow_name": self.workflow_name,
            "token": self.token,
            "environment": self.environment or "dev",
            "enabled": bool(self.enabled),
            "has_secret": bool(self.secret_header),
            "secret_header": self.secret_header,
            "parameter_mapping": json.loads(self.parameter_mapping_json or "{}"),
            "trigger_count": self.trigger_count or 0,
            "last_triggered_at": self.last_triggered_at,
            "created_at": self.created_at,
        }
