"""
User Management Workflow - Simplified user operations using unified framework
"""

from typing import Dict
from valiant import Workflow, step, InputField, workflow


@workflow("user_management")
class UserManagementWorkflow(Workflow):
    """Simple user management operations"""
    
    name = "User Management"
    description = "Basic user account management operations"
    version = "2.0.0"
    tags = ["user", "management", "admin"]
    
    def inputs(self):
        return [
            InputField("username", type="text", required=True,
                      help_text="Username for the account"),
            InputField("email", type="email", required=True,
                      help_text="User's email address"),
            InputField("action", type="select", 
                      options=["create", "update", "delete", "verify"],
                      default="create", help_text="Action to perform"),
            InputField("role", type="select",
                      options=["user", "admin", "viewer"], default="user",
                      help_text="User role assignment")
        ]
    
    @step("Validate User Data", order=1, tags=["validation"])
    def validate_user_data(self, context: Dict):
        """Validate user input data"""
        username = context.get("username", "").strip()
        email = context.get("email", "").strip()
        action = context.get("action")
        
        if not username or len(username) < 3:
            return self.failure("Username must be at least 3 characters")
        
        if not email or "@" not in email:
            return self.failure("Valid email address is required")
        
        # Store validated data
        context["validated_user"] = {
            "username": username.lower(),
            "email": email.lower(),
            "action": action,
            "role": context.get("role", "user")
        }
        
        result = self.success(f"User data validated for {username}")
        result.add_metric("username_length", len(username))
        result.add_tag("validation")
        
        return result
    
    @step("Execute User Action", order=2, tags=["processing"])
    def execute_user_action(self, context: Dict):
        """Execute the requested user action"""
        user_data = context.get("validated_user", {})
        action = user_data.get("action")
        username = user_data.get("username")
        
        if not user_data:
            return self.failure("No validated user data found")
        
        # Simulate different actions
        if action == "create":
            result_message = f"User account created for {username}"
            context["user_id"] = f"user_{hash(username) % 10000}"
        elif action == "update":
            result_message = f"User account updated for {username}"
            context["user_id"] = f"user_{hash(username) % 10000}"
        elif action == "delete":
            result_message = f"User account deleted for {username}"
            context["user_id"] = None
        elif action == "verify":
            result_message = f"User account verified for {username}"
            context["user_id"] = f"user_{hash(username) % 10000}"
        else:
            return self.failure(f"Unknown action: {action}")
        
        context["action_result"] = {
            "action": action,
            "username": username,
            "success": True,
            "timestamp": "2025-10-02T00:00:00Z"
        }
        
        result = self.success(result_message)
        result.add_metric("action_type", action)
        result.add_metric("user_role", user_data.get("role"))
        result.add_tag("user-management")
        result.add_tag(f"action-{action}")
        
        return result
    
    @step("Log Activity", order=3, tags=["logging"])
    def log_activity(self, context: Dict):
        """Log the user management activity"""
        user_data = context.get("validated_user", {})
        action_result = context.get("action_result", {})
        
        if not action_result:
            return self.failure("No action result to log")
        
        log_entry = {
            "timestamp": action_result.get("timestamp"),
            "action": action_result.get("action"),
            "username": action_result.get("username"),
            "email": user_data.get("email"),
            "role": user_data.get("role"),
            "status": "completed",
            "user_id": context.get("user_id")
        }
        
        context["activity_log"] = log_entry
        
        result = self.success("Activity logged successfully")
        result.add_metric("log_entries", 1)
        result.add_tag("logging")
        result.add_tag("audit")
        
        return result