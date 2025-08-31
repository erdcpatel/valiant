"""
Enhanced Demo Workflow - Demonstrates Phase 1 & 2 Enhanced Framework Features

This workflow showcases:
- Decorator-based step registration (@step)
- Pre-built step templates
- Enhanced error handling
- Automatic step discovery
- Rich metadata and validation
"""

from typing import Dict, List, Tuple, Any
from valiant.framework.enhanced_workflow import EnhancedBaseWorkflow
from valiant.framework.decorators import step, EnhancedStepResult, StepPriority
from valiant.framework.workflow import InputField, InputType, WorkflowMetadata


class EnhancedDemoWorkflow(EnhancedBaseWorkflow):
    """
    Enhanced Demo Workflow showcasing new framework features.
    
    This workflow demonstrates:
    - @step decorator with automatic discovery
    - Enhanced error handling and results
    - Rich input validation
    - Step metadata and priorities
    - Pre-built template integration
    """
    
    def get_metadata(self) -> WorkflowMetadata:
        return WorkflowMetadata(
            name="Enhanced Demo Workflow",
            description="Demonstrates Phase 1 & 2 enhanced framework features including decorators, templates, and automatic step discovery",
            version="1.0.0",
            author="Valiant Enhanced Framework",
            category="demo",
            tags=["enhanced", "demo", "decorators", "templates"],
            estimated_duration="30 seconds"
        )
    
    def get_required_inputs(self) -> List[Tuple[str, str, bool]]:
        """For CLI compatibility: returns list of (prompt, key, is_secret) tuples."""
        fields = self._get_input_fields_impl()
        return [
            (field.label, field.name, field.type == InputType.PASSWORD)
            for field in fields
        ]

    def _get_input_fields_impl(self) -> List[InputField]:
        return [
            InputField(
                name="demo_text",
                label="Demo Text Input",
                type=InputType.TEXT,
                required=True,
                default="Hello Enhanced Framework!",
                help_text="Text to process in the demo workflow",
                validation_regex=r"^.{3,100}$",
                validation_message="Text must be 3-100 characters"
            ),
            InputField(
                name="demo_number",
                label="Demo Number",
                type=InputType.NUMBER,
                required=True,
                default=42,
                help_text="Number for mathematical operations",
                min_value=1,
                max_value=1000
            ),
            InputField(
                name="demo_select",
                label="Demo Selection",
                type=InputType.SELECT,
                required=True,
                default="option1",
                options=["option1", "option2", "option3"],
                help_text="Select processing mode"
            ),
            InputField(
                name="enable_advanced",
                label="Enable Advanced Features",
                type=InputType.BOOLEAN,
                required=False,
                default=False,
                help_text="Enable advanced processing features"
            ),
            InputField(
                name="demo_date",
                label="Demo Date",
                type=InputType.DATE,
                required=False,
                help_text="Optional date for time-based processing"
            )
        ]
    
    @step(
        name="Initialize Context",
        order=1,
        description="Initialize workflow context with input validation",
        tags=["initialization", "validation"],
        priority=StepPriority.HIGH,
        timeout=10
    )
    def initialize_context(self, context: Dict) -> EnhancedStepResult:
        """Initialize and validate the workflow context"""
        try:
            demo_text = context.get("demo_text", "")
            demo_number = context.get("demo_number", 0)
            demo_select = context.get("demo_select", "")
            
            if not demo_text or len(demo_text) < 3:
                return EnhancedStepResult.create_failure(
                    "Initialize Context",
                    "Demo text is required and must be at least 3 characters",
                    {"validation_error": "demo_text"}
                )
            
            if int(demo_number) < 1 or int(demo_number) > 1000:
                return EnhancedStepResult.create_failure(
                    "Initialize Context",
                    "Demo number must be between 1 and 1000",
                    {"validation_error": "demo_number"}
                )
            
            context["processed_text"] = demo_text.upper()
            context["calculated_value"] = demo_number * 2
            context["processing_mode"] = demo_select
            context["workflow_start_time"] = "2025-08-31T07:30:00Z"
            
            return EnhancedStepResult.create_success(
                "Initialize Context",
                f"Context initialized successfully with text: '{demo_text}' and number: {demo_number}",
                {
                    "processed_text": context["processed_text"],
                    "calculated_value": context["calculated_value"],
                    "processing_mode": context["processing_mode"]
                }
            ).add_metadata("input_count", len(context)).add_tag("initialization")
            
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Initialize Context",
                f"Context initialization failed: {str(e)}",
                exception=e
            )
    
    @step(
        name="Process Text Data",
        order=2,
        description="Process and transform text data using enhanced features",
        tags=["processing", "text"],
        priority=StepPriority.NORMAL,
        requires=["Initialize Context"],
        timeout=15
    )
    def process_text_data(self, context: Dict) -> EnhancedStepResult:
        """Process text data with enhanced transformations"""
        try:
            processed_text = context.get("processed_text", "")
            processing_mode = context.get("processing_mode", "option1")
            
            if not processed_text:
                return EnhancedStepResult.create_failure(
                    "Process Text Data",
                    "No processed text found in context"
                )
            
            if processing_mode == "option1":
                result_text = f"BASIC: {processed_text}"
                complexity = "basic"
            elif processing_mode == "option2":
                result_text = f"ADVANCED: {processed_text[::-1]}"  # Reverse text
                complexity = "advanced"
            elif processing_mode == "option3":
                result_text = f"EXPERT: {''.join(c for i, c in enumerate(processed_text) if i % 2 == 0)}"
                complexity = "expert"
            else:
                result_text = processed_text
                complexity = "unknown"
            
            context["final_text"] = result_text
            context["text_length"] = len(result_text)
            context["complexity_level"] = complexity
            
            return EnhancedStepResult.create_success(
                "Process Text Data",
                f"Text processed successfully using {complexity} mode",
                {
                    "final_text": result_text,
                    "text_length": len(result_text),
                    "complexity": complexity
                }
            ).add_metadata("processing_mode", processing_mode).add_tag("text-processing")
            
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Process Text Data",
                f"Text processing failed: {str(e)}",
                exception=e
            )
    
    @step(
        name="Mathematical Operations",
        order=3,
        description="Perform mathematical calculations with validation",
        tags=["math", "calculation"],
        priority=StepPriority.NORMAL,
        parallel_group="data_processing",
        timeout=10
    )
    def mathematical_operations(self, context: Dict) -> EnhancedStepResult:
        """Perform mathematical operations on the demo number"""
        try:
            calculated_value = int(context.get("calculated_value", 0))
            demo_number = int(context.get("demo_number", 0))
            enable_advanced = context.get("enable_advanced", False)
            
            if calculated_value == 0:
                return EnhancedStepResult.create_failure(
                    "Mathematical Operations",
                    "No calculated value found in context"
                )
            
            squared = calculated_value ** 2
            factorial_base = min(demo_number, 10)  # Limit factorial to prevent overflow
            factorial = 1
            for i in range(1, factorial_base + 1):
                factorial *= i
            
            results = {
                "original": demo_number,
                "doubled": calculated_value,
                "squared": squared,
                "factorial": factorial
            }
            
            if enable_advanced:
                results["cube"] = calculated_value ** 3
                results["square_root"] = calculated_value ** 0.5
                results["fibonacci"] = self._fibonacci(min(demo_number, 20))
            
            context["math_results"] = results
            context["calculation_count"] = len(results)
            
            return EnhancedStepResult.create_success(
                "Mathematical Operations",
                f"Mathematical operations completed. Calculated {len(results)} values.",
                results
            ).add_metadata("advanced_enabled", enable_advanced).add_tag("mathematics")
            
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Mathematical Operations",
                f"Mathematical operations failed: {str(e)}",
                exception=e
            )
    
    @step(
        name="Data Validation",
        order=4,
        description="Validate processed data and results",
        tags=["validation", "quality"],
        priority=StepPriority.HIGH,
        parallel_group="data_processing",
        timeout=10
    )
    def data_validation(self, context: Dict) -> EnhancedStepResult:
        """Validate all processed data for consistency and quality"""
        try:
            validation_results = {}
            errors = []
            warnings = []
            
            final_text = context.get("final_text", "")
            if final_text:
                validation_results["text_valid"] = True
                validation_results["text_length"] = len(final_text)
            else:
                errors.append("Final text is missing or empty")
                validation_results["text_valid"] = False
            
            math_results = context.get("math_results", {})
            if math_results:
                validation_results["math_valid"] = True
                validation_results["calculation_count"] = len(math_results)
                
                if math_results.get("squared", 0) > 1000000:
                    warnings.append("Squared value is very large")
                
                if math_results.get("factorial", 0) > 3628800:  # 10!
                    warnings.append("Factorial value is at maximum limit")
            else:
                errors.append("Mathematical results are missing")
                validation_results["math_valid"] = False
            
            validation_results["errors"] = errors
            validation_results["warnings"] = warnings
            validation_results["overall_valid"] = len(errors) == 0
            
            context["validation_results"] = validation_results
            
            if errors:
                return EnhancedStepResult.create_failure(
                    "Data Validation",
                    f"Validation failed with {len(errors)} errors: {', '.join(errors)}",
                    validation_results
                )
            
            message = "Data validation passed successfully"
            if warnings:
                message += f" with {len(warnings)} warnings"
            
            return EnhancedStepResult.create_success(
                "Data Validation",
                message,
                validation_results
            ).add_metadata("warning_count", len(warnings)).add_tag("validation")
            
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Data Validation",
                f"Data validation failed: {str(e)}",
                exception=e
            )
    
    @step(
        name="Generate Report",
        order=5,
        description="Generate comprehensive workflow report",
        tags=["reporting", "summary"],
        priority=StepPriority.LOW,
        requires=["Process Text Data", "Mathematical Operations", "Data Validation"],
        timeout=15
    )
    def generate_report(self, context: Dict) -> EnhancedStepResult:
        """Generate a comprehensive report of all workflow results"""
        try:
            report = {
                "workflow_name": "Enhanced Demo Workflow",
                "execution_summary": {},
                "input_data": {},
                "processing_results": {},
                "validation_summary": {},
                "metadata": {}
            }
            
            report["input_data"] = {
                "demo_text": context.get("demo_text", ""),
                "demo_number": context.get("demo_number", 0),
                "demo_select": context.get("demo_select", ""),
                "enable_advanced": context.get("enable_advanced", False),
                "demo_date": context.get("demo_date", "")
            }
            
            report["processing_results"] = {
                "final_text": context.get("final_text", ""),
                "text_length": context.get("text_length", 0),
                "complexity_level": context.get("complexity_level", ""),
                "math_results": context.get("math_results", {}),
                "calculation_count": context.get("calculation_count", 0)
            }
            
            validation_results = context.get("validation_results", {})
            report["validation_summary"] = {
                "overall_valid": validation_results.get("overall_valid", False),
                "error_count": len(validation_results.get("errors", [])),
                "warning_count": len(validation_results.get("warnings", [])),
                "text_valid": validation_results.get("text_valid", False),
                "math_valid": validation_results.get("math_valid", False)
            }
            
            report["metadata"] = {
                "workflow_version": "1.0.0",
                "framework_type": "enhanced",
                "step_count": 5,
                "parallel_groups": ["data_processing"],
                "execution_time": "simulated",
                "enhanced_features_used": [
                    "decorator_registration",
                    "automatic_discovery",
                    "enhanced_results",
                    "parallel_execution",
                    "rich_validation"
                ]
            }
            
            report["execution_summary"] = {
                "status": "completed",
                "total_steps": 5,
                "successful_steps": 5,
                "failed_steps": 0,
                "data_quality": "high" if validation_results.get("overall_valid") else "low",
                "processing_mode": context.get("processing_mode", "unknown")
            }
            
            context["final_report"] = report
            
            return EnhancedStepResult.create_success(
                "Generate Report",
                "Comprehensive workflow report generated successfully",
                report
            ).add_metadata("report_sections", len(report)).add_tag("reporting")
            
        except Exception as e:
            return EnhancedStepResult.create_failure(
                "Generate Report",
                f"Report generation failed: {str(e)}",
                exception=e
            )
    
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number (helper method)"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
