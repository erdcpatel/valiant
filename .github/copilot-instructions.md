# Valiant Workflow Automation Platform - AI Coding Instructions

## Architecture Overview

**Valiant** is a **streamlined Python workflow automation platform** with a **unified architecture** designed for simplicity and developer productivity:

- **Single Framework**: Unified `Workflow` base class with decorator-based `@step` registration
- **Simple Imports**: `from valiant import Workflow, step, workflow, InputField, InputType`
- **Auto-Discovery**: Workflows automatically discovered and registered
- **Clean Patterns**: Minimal boilerplate, intuitive API design

### Key Components

- **Framework Core**: `valiant/framework/workflow_unified.py` - unified workflow engine
- **Workflow Registry**: `valiant/workflows/config.py` - maps workflow names to class paths
- **CLI Entry**: `run.py` → `valiant/cli.py` - typer-based command interface with `--set` parameter support
- **Dual UI**: FastAPI (port 8000) + Streamlit (port 8501) with shared backend

## Workflow Development Patterns

### Unified Workflow Architecture (Recommended)
Use the single `Workflow` base class with `@step` decorators:

```python
from valiant import Workflow, step, workflow, InputField, InputType

@workflow(name="my_workflow")
class MyWorkflow(Workflow):
    def get_input_fields(self):
        return [
            InputField(name="username", type=InputType.TEXT, required=True),
            InputField(name="action", type=InputType.SELECT, 
                      options=["create", "update", "delete"], required=True)
        ]
    
    @step(name="Process-User", order=1)
    def process_user(self, context):
        username = context.get("username")
        action = context.get("action")
        
        # Business logic here
        result = self.success(f"Processed {action} for {username}")
        result.add_metric("processing_time", 1.5)
        result.add_tag("user-management")
        return result
```

### Critical Implementation Requirements
- **Single Import**: Always use `from valiant import Workflow, step, workflow`
- **Step Results**: Return `self.success()`, `self.failure()`, or `self.skip()` from workflow methods
- **Metrics & Tags**: Use `result.add_metric(key, value)` and `result.add_tag(tag)` for rich reporting
- **Context Management**: Access/modify `context` dict for inter-step data flow
- **Input Validation**: Implement `get_input_fields()` with `InputField` objects

### Step Result Methods
```python
# Success with optional data, metrics, and tags
return self.success(
    message="Operation completed successfully",
    data={"processed_items": 42},
    metrics={"duration": 2.5, "items_processed": 42},
    tags=["processing", "success"]
)

# Failure with error message
return self.failure("Operation failed: invalid input")

# Skip step conditionally
return self.skip("Skipping due to condition not met")
```

## Development Workflow Commands

### Service Management
```bash
cd valiant/ui
bash start_services.sh start     # Start both FastAPI + Streamlit
bash start_services.sh stop      # Stop both services
bash start_services.sh status    # Check service status
bash start_services.sh logs fastapi  # View specific service logs
```

### CLI Execution
```bash
python run.py run <workflow_name>                    # Interactive mode
python run.py run <workflow_name> --set key=value   # Provide context parameters
python run.py list                                  # List available workflows
```

### Workflow Registration
Workflows are auto-discovered using the `@workflow` decorator, or manually registered in `valiant/workflows/config.py`:
```python
WORKFLOWS = {
    "my_workflow": "valiant.workflows.my_workflow.MyWorkflowClass"
}
```

## Project-Specific Conventions

### File Structure Patterns
- **Workflow Files**: Direct files in `valiant/workflows/` (e.g., `demo.py`, `user_management.py`)
- **Configuration**: `valiant/config/application*.yaml` for environment settings
- **Service Scripts**: `valiant/ui/start_services.sh` handles PYTHONPATH and process management

### Context Flow Architecture
1. **Input Collection**: CLI prompts or `--set` parameters populate context
2. **Step Execution**: Each step receives/modifies shared context dict
3. **Result Aggregation**: Engine collects `StepResult` objects with metrics/tags
4. **Output Formatting**: Support for `--output json` or rich console display

### Error Handling Patterns
- **Step Failures**: Return `self.failure(message)` with descriptive messages
- **Validation**: Use `InputField` validation (type, options, required) for inputs
- **Exception Handling**: Framework catches exceptions and converts to failure results

## Integration Points

### Framework Engine Integration
- **Step Registration**: Automatic discovery via `@step` decorators
- **Parallel Execution**: Use `parallel_group` parameter for concurrent step execution
- **Timeout/Retries**: Configure per-step via `@step` decorator parameters

### UI/API Integration
- **FastAPI Backend**: Auto-exposes workflows via `/workflows` and `/run/{workflow_name}` endpoints
- **Streamlit Frontend**: Dynamic form generation from `InputField` definitions
- **Context Persistence**: Optional debugging with context data

### External Dependencies
- **API Calls**: Use standard Python requests or utilities from `valiant.framework.utils`
- **CLI Commands**: Use subprocess or shell commands within step methods
- **Configuration**: Load environment-specific settings from `valiant/config/`

## Common Anti-Patterns to Avoid

❌ **Complex inheritance hierarchies** - use single `Workflow` base class
❌ **Missing error handling** - always return proper result objects from step methods
❌ **Hardcoded values** - use context and configuration for environment-specific data
❌ **Manual step registration** - use `@step` decorators for automatic discovery
❌ **Missing input validation** - define proper `InputField` specifications

## Testing and Debugging

### Test Workflow Execution
```bash
python run.py run demo --set user_name="test" --set user_email="test@example.com"
python run.py run user_management --set username=testuser --set action=create
```

### Debug Output
- **Verbose Mode**: Check console output for detailed step execution
- **Context Inspection**: Parameters passed via `--set` are available in context
- **Service Logs**: Check `valiant/ui/logs/` for FastAPI/Streamlit errors
- **Step Results**: Look for success/failure messages and metrics in output

Focus on the unified architecture, simple import patterns, and decorator-based step registration when working with this codebase.