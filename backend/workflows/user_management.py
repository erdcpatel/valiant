"""
User Management Workflow - Handles user provisioning with sensitive password handling.
"""
from backend.valiant import Workflow, step, workflow, InputField, InputType


@workflow(
    name="user_management",
    description="Provision and verify user accounts with password redaction and role checks",
    tags=["admin", "security", "users"]
)
class UserManagementWorkflow(Workflow):
    name = "User Provisioning"
    description = "Create and configure application user accounts"
    version = "3.0.0"
    tags = ["users", "security"]

    def inputs(self):
        return [
            InputField("username", type=InputType.TEXT, required=True, default="john_doe"),
            InputField("email", type=InputType.EMAIL, required=True, default="john@example.com"),
            InputField("temporary_password", type=InputType.PASSWORD, required=True, default="SecretPass123!"),
            InputField("role", type=InputType.SELECT, options=["viewer", "editor", "admin"], default="viewer")
        ]

    @step("Validate Credentials", order=1, tags=["security"])
    def validate_credentials(self, context):
        username = context.get("username", "")
        email = context.get("email", "")
        pwd = context.get("temporary_password", "")

        if len(username) < 3:
            return self.failure("Username must be at least 3 characters")
        if len(pwd) < 8:
            return self.failure("Password must be at least 8 characters")

        res = self.success(f"Credentials valid for {username} <{email}>")
        res.add_metric("username_length", len(username))
        return res

    @step("Create User Record", order=2, requires=["Validate Credentials"], tags=["database"])
    def create_user(self, context):
        username = context.get("username")
        role = context.get("role")
        user_id = f"usr_{hash(username) % 100000}"
        context["created_user_id"] = user_id

        res = self.success(f"Created account for '{username}' with role '{role}' (ID: {user_id})")
        res.add_metric("user_id", user_id)
        res.add_tag("audit-logged")
        return res

    @step("Assign Permissions", order=3, requires=["Create User Record"], tags=["security"])
    def assign_permissions(self, context):
        role = context.get("role")
        user_id = context.get("created_user_id")
        perms = ["read"] if role == "viewer" else ["read", "write"] if role == "editor" else ["read", "write", "admin"]
        context["assigned_permissions"] = perms

        res = self.success(f"Assigned permissions {perms} to user {user_id}")
        res.add_metric("permission_count", len(perms))
        return res
