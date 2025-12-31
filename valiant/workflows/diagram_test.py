"""
Diagram Test Workflow - Comprehensive test for Mermaid diagram visualization

This workflow demonstrates all diagram features including:
- Sequential steps
- Parallel execution groups
- Conditional steps
- Multiple parallel groups at different order levels
"""

from typing import Dict
from valiant import Workflow, step, workflow, InputField, InputType


@workflow("diagram_test")
class DiagramTestWorkflow(Workflow):
    """Test workflow for comprehensive diagram visualization"""
    
    name = "Diagram Test Workflow"
    description = "Tests all Mermaid diagram scenarios including parallel execution and conditional steps"
    version = "1.0.0"
    tags = ["test", "diagram", "visualization"]
    
    def get_input_fields(self):
        """Define input fields for the workflow"""
        return [
            InputField(name="enable_optional", type=InputType.BOOLEAN, 
                      label="Enable Optional Processing",
                      required=False,
                      default=True,
                      help_text="Enable optional data transformation step"),
            InputField(name="enable_advanced", type=InputType.BOOLEAN,
                      label="Enable Advanced Processing",
                      required=False,
                      default=False,
                      help_text="Enable advanced analytics step"),
        ]
    
    @step("Initialize-Workflow", order=1, tags=["setup", "initialization"])
    def initialize(self, context: Dict):
        """Initialize the workflow and prepare environment"""
        context["workflow_id"] = "diagram_test_001"
        context["start_time"] = "2025-12-31T10:00:00"
        
        result = self.success("Workflow initialized successfully")
        result.add_metric("initialization_time", 0.5)
        result.add_tag("setup")
        return result
    
    # Parallel data fetching at order 2
    @step("Fetch-Users", order=2, parallel_group="data_fetch", tags=["parallel", "data"])
    def fetch_users(self, context: Dict):
        """Fetch user data from database"""
        context["users"] = ["user1", "user2", "user3"]
        
        result = self.success("Users fetched successfully")
        result.add_metric("users_count", 3)
        result.add_tag("data-fetch")
        return result
    
    @step("Fetch-Products", order=2, parallel_group="data_fetch", tags=["parallel", "data"])
    def fetch_products(self, context: Dict):
        """Fetch product catalog"""
        context["products"] = ["product1", "product2", "product3", "product4"]
        
        result = self.success("Products fetched successfully")
        result.add_metric("products_count", 4)
        result.add_tag("data-fetch")
        return result
    
    @step("Fetch-Orders", order=2, parallel_group="data_fetch", tags=["parallel", "data"])
    def fetch_orders(self, context: Dict):
        """Fetch order history"""
        context["orders"] = ["order1", "order2"]
        
        result = self.success("Orders fetched successfully")
        result.add_metric("orders_count", 2)
        result.add_tag("data-fetch")
        return result
    
    # Sequential validation step
    @step("Validate-Data", order=3, tags=["validation", "quality"])
    def validate_data(self, context: Dict):
        """Validate all fetched data"""
        users = context.get("users", [])
        products = context.get("products", [])
        orders = context.get("orders", [])
        
        total_records = len(users) + len(products) + len(orders)
        context["validation_passed"] = total_records > 0
        
        result = self.success(f"Data validation completed: {total_records} records")
        result.add_metric("total_records", total_records)
        result.add_tag("validation")
        return result
    
    # Conditional step based on input
    @step("Optional-Processing", order=4, condition="enable_optional", 
          tags=["conditional", "optional"])
    def optional_processing(self, context: Dict):
        """Optional data processing step (runs if enabled)"""
        context["optional_data"] = "processed"
        
        result = self.success("Optional processing completed")
        result.add_metric("optional_items", 5)
        result.add_tag("optional")
        return result
    
    # Another parallel group at order 5 - data transformation
    @step("Transform-Users", order=5, parallel_group="transform", tags=["parallel", "transform"])
    def transform_users(self, context: Dict):
        """Transform user data for output"""
        users = context.get("users", [])
        context["transformed_users"] = [f"transformed_{u}" for u in users]
        
        result = self.success("User data transformed")
        result.add_metric("transformed_count", len(users))
        result.add_tag("transformation")
        return result
    
    @step("Transform-Products", order=5, parallel_group="transform", tags=["parallel", "transform"])
    def transform_products(self, context: Dict):
        """Transform product data for output"""
        products = context.get("products", [])
        context["transformed_products"] = [f"transformed_{p}" for p in products]
        
        result = self.success("Product data transformed")
        result.add_metric("transformed_count", len(products))
        result.add_tag("transformation")
        return result
    
    # Conditional advanced analytics
    @step("Advanced-Analytics", order=6, condition="enable_advanced",
          tags=["conditional", "analytics", "advanced"])
    def advanced_analytics(self, context: Dict):
        """Run advanced analytics if enabled"""
        context["analytics_results"] = {
            "total_users": len(context.get("users", [])),
            "total_products": len(context.get("products", [])),
            "conversion_rate": 0.15
        }
        
        result = self.success("Advanced analytics completed")
        result.add_metric("conversion_rate", 0.15)
        result.add_tag("analytics")
        return result
    
    # Final reporting step
    @step("Generate-Report", order=7, tags=["reporting", "final"])
    def generate_report(self, context: Dict):
        """Generate final workflow report"""
        report = {
            "workflow_id": context.get("workflow_id"),
            "users_processed": len(context.get("transformed_users", [])),
            "products_processed": len(context.get("transformed_products", [])),
            "optional_enabled": "optional_data" in context,
            "analytics_run": "analytics_results" in context
        }
        
        context["final_report"] = report
        
        result = self.success("Final report generated successfully")
        result.add_metric("report_sections", 5)
        result.add_tag("reporting")
        result.add_tag("complete")
        return result
