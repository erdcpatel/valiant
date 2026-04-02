"""
User Management workflow — demonstrates a realistic operational workflow
with input validation, external-call simulation, and conditional steps.

Run it:
    valiant run user_management --set username=alice --set email=alice@example.com --set role=editor
"""
from __future__ import annotations

import time

from valiant.core.context import WorkflowContext
from valiant.core.models import InputField, InputType, StepResult
from valiant.core.workflow import Workflow, step, workflow


@workflow(
    name="user_management",
    description="Create, validate and provision a new user account.",
    tags=["users", "onboarding"],
    version="3.0.0",
)
class UserManagementWorkflow(Workflow):

    def get_input_fields(self) -> list[InputField]:
        return [
            InputField(
                name="username",
                label="Username",
                type=InputType.TEXT,
                required=True,
                description="Alphanumeric, 3–32 characters",
            ),
            InputField(
                name="email",
                label="Email Address",
                type=InputType.EMAIL,
                required=True,
            ),
            InputField(
                name="role",
                label="Role",
                type=InputType.SELECT,
                required=True,
                options=["viewer", "editor", "admin"],
                default="viewer",
            ),
            InputField(
                name="send_welcome_email",
                label="Send Welcome Email",
                type=InputType.BOOLEAN,
                required=False,
                default=True,
            ),
            InputField(
                name="temp_password",
                label="Temporary Password",
                type=InputType.PASSWORD,
                required=False,
                sensitive=True,
                description="Leave blank to auto-generate",
            ),
        ]

    @step(name="Validate User Data", order=1)
    def validate(self, ctx: WorkflowContext) -> StepResult:
        username = ctx["username"].strip()
        email = ctx["email"].strip()
        role = ctx["role"]

        errors = []
        if not (3 <= len(username) <= 32):
            errors.append("Username must be 3–32 characters")
        if not username.isalnum():
            errors.append("Username must be alphanumeric")
        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Invalid email address")
        if role not in ["viewer", "editor", "admin"]:
            errors.append(f"Invalid role: {role!r}")

        if errors:
            return self.failure(
                "; ".join(errors),
                tags=["validation-failed"],
                metrics={"error_count": float(len(errors))},
            )

        return self.success(
            f"User data valid: {username} <{email}> as {role}",
            data={"username": username, "email": email, "role": role},
            tags=["validated"],
        )

    @step(name="Check Existing User", order=2, requires=["Validate User Data"])
    def check_existing(self, ctx: WorkflowContext) -> StepResult:
        username = ctx.get_data("Validate User Data", "username")
        time.sleep(0.1)  # simulate DB lookup

        # Simulate: no conflict found
        return self.success(
            f"Username '{username}' is available",
            data={"exists": False},
            metrics={"db_query_ms": 45.0},
            tags=["db-checked"],
        )

    @step(name="Create User Account", order=3, requires=["Check Existing User"])
    def create_account(self, ctx: WorkflowContext) -> StepResult:
        user_data = ctx.get_data("Validate User Data")
        time.sleep(0.15)  # simulate DB write

        user_id = f"usr_{user_data['username']}_001"
        return self.success(
            f"Account created with ID {user_id}",
            data={"user_id": user_id, "username": user_data["username"], "role": user_data["role"]},
            metrics={"accounts_created": 1.0},
            tags=["created"],
        )

    @step(name="Send Welcome Email", order=4, requires=["Create User Account"])
    def send_email(self, ctx: WorkflowContext) -> StepResult:
        if not ctx.get("send_welcome_email", True):
            return self.skip("Welcome email disabled by input")

        email = ctx.get_data("Validate User Data", "email")
        user_id = ctx.get_data("Create User Account", "user_id")
        time.sleep(0.05)

        return self.success(
            f"Welcome email sent to {email}",
            data={"user_id": user_id, "email": email},
            metrics={"emails_sent": 1.0},
            tags=["email-sent"],
        )
