"""
Core Data Models for Valiant Workflow Platform
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
import re
import time
from datetime import datetime


class InputType(str, Enum):
    """Supported input field types for workflow parameters."""
    TEXT = "text"
    PASSWORD = "password"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    DATE = "date"
    EMAIL = "email"
    CHECKBOX = "checkbox"
    JSON = "json"


class InputField(BaseModel):
    """Defines an input parameter expected by a workflow."""
    name: str
    type: InputType = InputType.TEXT
    label: Optional[str] = None
    required: bool = True
    default: Any = None
    help_text: Optional[str] = None
    options: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    validation_regex: Optional[str] = None
    validation_message: Optional[str] = None
    sensitive: bool = False

    def __init__(self, name: str = "", **data):
        super().__init__(name=name, **data)

    def model_post_init(self, __context: Any) -> None:
        if self.label is None:
            self.label = self.name.replace("_", " ").title()
        if self.type == InputType.PASSWORD:
            self.sensitive = True

    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate an input value against field rules."""
        if self.required and (value is None or value == ""):
            return False, f"{self.label} is required"

        if value is None or value == "":
            return True, ""

        if self.type == InputType.NUMBER:
            try:
                num = float(value)
                if self.min_value is not None and num < self.min_value:
                    return False, f"{self.label} must be at least {self.min_value}"
                if self.max_value is not None and num > self.max_value:
                    return False, f"{self.label} must be at most {self.max_value}"
            except (ValueError, TypeError):
                return False, f"{self.label} must be a valid number"

        elif self.type == InputType.SELECT:
            if self.options and str(value) not in self.options:
                return False, f"{self.label} must be one of: {', '.join(self.options)}"

        elif self.type == InputType.EMAIL:
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value)):
                return False, f"{self.label} must be a valid email address"

        if self.validation_regex:
            if not re.match(self.validation_regex, str(value)):
                return False, self.validation_message or f"{self.label} format is invalid"

        return True, ""


class StepPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    REJECTED = "rejected"


class StepConfig(BaseModel):
    """Configuration metadata for a workflow step."""
    name: str
    order: int = 100
    timeout: float = 30.0
    retries: int = 0
    parallel_group: Optional[str] = None
    requires: List[str] = Field(default_factory=list)
    priority: StepPriority = StepPriority.MEDIUM
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True
    condition: Optional[str] = None
    requires_approval: bool = False
    approval_prompt: Optional[str] = None
    approval_roles: List[str] = Field(default_factory=list)


class StepContextDelta(BaseModel):
    """Context mutations and access telemetry for a step."""
    reads: List[str] = Field(default_factory=list)
    added: Dict[str, Any] = Field(default_factory=dict)
    modified: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # key -> {"before": v1, "after": v2}
    deleted: List[str] = Field(default_factory=list)


class StepLineage(BaseModel):
    """Data provenance showing upstream producer steps and downstream consumers."""
    upstream_sources: Dict[str, str] = Field(default_factory=dict)  # context_key -> producer step name / "inputs"
    downstream_targets: Dict[str, List[str]] = Field(default_factory=dict)  # context_key -> [consumer step names]


class StepResult(BaseModel):
    """Result of an executed or evaluated step."""
    name: str
    order: int = 100
    parallel_group: Optional[str] = None
    requires: List[str] = Field(default_factory=list)
    condition: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    success: bool = False
    message: str = ""
    data: Any = None
    skipped: bool = False
    executed: bool = False
    reused: bool = False
    context_before: Optional[Dict[str, Any]] = None
    context_snapshot: Optional[Dict[str, Any]] = None
    context_delta: Optional[StepContextDelta] = None
    lineage: Optional[StepLineage] = None
    time_taken: float = 0.0
    attempts: int = 1
    error: Optional[str] = None
    requires_approval: bool = False
    approval_prompt: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    approval_notes: Optional[str] = None
    tabular_data: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_metric(self, key: str, value: Any) -> "StepResult":
        self.metrics[key] = value
        return self

    def add_tag(self, tag: str) -> "StepResult":
        if tag not in self.tags:
            self.tags.append(tag)
        return self

    def log(self, line: str) -> "StepResult":
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.logs.append(f"[{timestamp}] {line}")
        return self


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowResult(BaseModel):
    """Comprehensive summary of a full workflow run."""
    workflow_name: str
    run_id: str
    parent_run_id: Optional[str] = None
    resumed_from_step: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    success: bool = False
    total_steps: int = 0
    executed_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    total_time: float = 0.0
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    results: List[StepResult] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    environment: str = "dev"
    profile: Optional[str] = None
    error: Optional[str] = None


class RunEventType(str, Enum):
    RUN_STARTED = "run_started"
    STEP_STARTED = "step_started"
    STEP_LOG = "step_log"
    STEP_FINISHED = "step_finished"
    STEP_WAITING_APPROVAL = "step_waiting_approval"
    STEP_APPROVED = "step_approved"
    STEP_REJECTED = "step_rejected"
    RUN_FINISHED = "run_finished"
    RUN_CANCELLED = "run_cancelled"


class RunEvent(BaseModel):
    """Live streaming event sent to UI/WebSocket clients."""
    run_id: str
    event_type: RunEventType
    timestamp: float = Field(default_factory=time.time)
    step_name: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
