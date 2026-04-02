"""Custom exceptions for Valiant."""
from __future__ import annotations


class ValiantError(Exception):
    """Base exception for all Valiant errors."""


class WorkflowNotFoundError(ValiantError):
    """Raised when a workflow name cannot be resolved in the registry."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Workflow '{name}' not found. Run 'valiant list' to see available workflows.")
        self.name = name


class WorkflowValidationError(ValiantError):
    """Raised when workflow inputs fail validation."""

    def __init__(self, errors: dict[str, str]) -> None:
        messages = "; ".join(f"{k}: {v}" for k, v in errors.items())
        super().__init__(f"Input validation failed — {messages}")
        self.errors = errors


class StepExecutionError(ValiantError):
    """Raised when a step raises an unhandled exception."""

    def __init__(self, step_name: str, cause: Exception) -> None:
        super().__init__(f"Step '{step_name}' raised {type(cause).__name__}: {cause}")
        self.step_name = step_name
        self.cause = cause


class WorkflowAlreadyRegisteredError(ValiantError):
    """Raised when two workflows register under the same name."""

    def __init__(self, name: str) -> None:
        super().__init__(f"A workflow named '{name}' is already registered.")
        self.name = name
