"""
Demo Workflow - Streamlined example using the unified Valiant framework

This workflow demonstrates the simplified, unified approach to creating
workflows in Valiant with clean decorators and simple return values.
"""

from typing import Dict
from valiant import Workflow, step, InputField, InputType, workflow


@workflow("demo")
class DemoWorkflow(Workflow):
    """Simple demonstration workflow showcasing unified framework features"""
    
    name = "Demo Workflow"
    description = "A streamlined demonstration of the unified Valiant framework"
    version = "2.0.0"
    author = "Valiant Team"
    tags = ["demo", "example", "unified"]
    
    def inputs(self):
        """Define input fields for the workflow"""
        return [
            InputField("user_name", type="text", required=True, 
                      help_text="Name of the user to process"),
            InputField("user_email", type="email", required=True,
                      help_text="Email address for notifications"),
            InputField("processing_mode", type="select", 
                      options=["basic", "advanced", "expert"], default="basic",
                      help_text="Level of processing to perform"),
            InputField("send_notification", type="checkbox", default=True,
                      help_text="Send completion notification"),
            InputField("max_items", type="number", min_value=1, max_value=100, 
                      default=10, help_text="Maximum items to process")
        ]
    
    @step("Validate Input", order=1, tags=["validation"])
    def validate_input(self, context: Dict):
        """Validate user input and prepare for processing"""
        user_name = context.get("user_name", "").strip()
        user_email = context.get("user_email", "").strip()
        
        if not user_name:
            return self.failure("User name is required")
        
        if len(user_name) < 2:
            return self.failure("User name must be at least 2 characters")
        
        if not user_email or "@" not in user_email:
            return self.failure("Valid email address is required")
        
        # Store validated data
        context["validated_user"] = {
            "name": user_name.title(),
            "email": user_email.lower(),
            "id": f"user_{hash(user_email) % 10000}"
        }
        
        result = self.success(f"Input validated for user: {user_name}")
        result.add_metric("user_name_length", len(user_name))
        result.add_metric("email_domain", user_email.split("@")[1])
        result.add_tag("input-validation")
        
        return result
    
    @step("Process Data", order=2, tags=["processing"])
    def process_data(self, context: Dict):
        """Process user data based on selected mode"""
        user = context.get("validated_user", {})
        mode = context.get("processing_mode", "basic")
        max_items = int(context.get("max_items", 10))
        
        if not user:
            return self.failure("No validated user data found")
        
        # Simulate different processing modes
        processed_items = []
        complexity = "unknown"  # Initialize with default value
        
        if mode == "basic":
            processed_items = [f"Item {i+1} for {user['name']}" for i in range(min(max_items, 5))]
            complexity = "low"
        elif mode == "advanced":
            processed_items = [f"Advanced Item {i+1}: {user['email']}" for i in range(min(max_items, 10))]
            complexity = "medium"
        elif mode == "expert":
            processed_items = [f"Expert Item {i+1}: ID-{user['id']}" for i in range(max_items)]
            complexity = "high"
        else:
            # Handle unexpected mode values
            processed_items = [f"Default Item {i+1}" for i in range(min(max_items, 3))]
            complexity = "default"
        
        context["processed_data"] = {
            "items": processed_items,
            "count": len(processed_items),
            "mode": mode,
            "user_id": user["id"]
        }
        
        result = self.success(f"Processed {len(processed_items)} items in {mode} mode")
        result.add_metric("items_processed", len(processed_items))
        result.add_metric("processing_mode", mode)
        result.add_metric("complexity_level", complexity)
        result.add_tag("data-processing")
        result.add_tag(f"mode-{mode}")
        
        return result
    
    @step("Generate Report", order=3, tags=["reporting"])
    def generate_report(self, context: Dict):
        """Generate processing report"""
        user = context.get("validated_user", {})
        processed = context.get("processed_data", {})
        
        if not user or not processed:
            return self.failure("Missing required data for report generation")
        
        report = {
            "user_info": {
                "name": user["name"],
                "email": user["email"],
                "id": user["id"]
            },
            "processing_summary": {
                "mode": processed["mode"],
                "items_processed": processed["count"],
                "items": processed["items"][:3]  # Show first 3 items
            },
            "workflow_info": {
                "name": self.name,
                "version": self.version,
                "execution_time": "simulated"
            }
        }
        
        context["final_report"] = report
        
        result = self.success(f"Report generated for {user['name']}")
        result.add_metric("report_sections", len(report))
        result.add_metric("summary_items", len(report["processing_summary"]["items"]))
        result.add_tag("reporting")
        
        return result
    
    @step("Send Notification", order=4, condition="send_notification", tags=["notification"])
    def send_notification(self, context: Dict):
        """Send completion notification if enabled"""
        user = context.get("validated_user", {})
        processed = context.get("processed_data", {})
        
        if not context.get("send_notification"):
            return self.skip("Notification disabled by user")
        
        if not user:
            return self.failure("No user data available for notification")
        
        # Simulate sending notification
        notification_content = {
            "to": user["email"],
            "subject": f"Processing Complete for {user['name']}",
            "message": f"Successfully processed {processed.get('count', 0)} items",
            "type": "completion"
        }
        
        context["notification_sent"] = notification_content
        
        result = self.success(f"Notification sent to {user['email']}")
        result.add_metric("notification_type", "email")
        result.add_metric("recipient_count", 1)
        result.add_tag("notification")
        result.add_tag("email")
        
        return result