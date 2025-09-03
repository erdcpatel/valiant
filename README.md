
# Valiant Workflow Automation Platform

Valiant is an extensible Python platform for automating, orchestrating, and validating complex workflows. It supports modern UI, REST API, and CLI interfaces, with advanced features for metrics, tagging, templates, and developer productivity.

---

## Requirements & Environment

- **Python**: 3.10+ recommended (tested on 3.10, 3.11, 3.12)
- **OS**: Linux, macOS, Windows (WSL recommended)
- **Dependencies**:
  - Core: `requirements.txt`
  - UI/API: `requirements-ui.txt`
- **Recommended**: Use a virtual environment (venv, conda)

### Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-ui.txt
```

---




## Service Management

The `start_services.sh` script manages both UI and API services:
```bash
cd valiant/ui
bash start_services.sh start      # Start both services
bash start_services.sh stop       # Stop both services
bash start_services.sh restart    # Restart both services
bash start_services.sh status     # Check service status
bash start_services.sh logs fastapi    # View FastAPI logs
bash start_services.sh logs streamlit  # View Streamlit logs
bash start_services.sh clean      # Clean log and PID files
```

---


  - `GET /workflows`
          "demo_number": 42,

## Workflow Development

### Add a New Workflow
1. Create a Python file in `valiant/workflows/`
2. Subclass `EnhancedBaseWorkflow` (recommended) or `BaseWorkflow`
3. Define input fields via `_get_input_fields_impl()`
4. Register steps using the `@step` decorator or templates
5. Register your workflow in `valiant/workflows/config.py`

### Example: Enhanced Workflow
```python
from valiant.framework.enhanced_workflow import EnhancedBaseWorkflow
from valiant.framework.decorators import step, EnhancedStepResult
from valiant.framework.workflow import InputField, InputType

class MyWorkflow(EnhancedBaseWorkflow):
  def _get_input_fields_impl(self):
    return [
      InputField(name="username", type=InputType.TEXT, label="Username"),
      InputField(name="password", type=InputType.PASSWORD, label="Password")
    ]

  @step(name="Authenticate", order=1)
  def authenticate(self, context):
    # ... authentication logic ...
    return EnhancedStepResult.create_success("Authenticate", "Authenticated")
```

### Templates & Builder Pattern
```python
from valiant.framework.enhanced_workflow import WorkflowBuilder

workflow = (WorkflowBuilder(EnhancedBaseWorkflow)
  .add_auth_step(name="Login", url="/auth/login")
  .add_api_get_step(name="Get-Profile", url="/user/profile", requires_auth=True)
  .add_cli_step(name="Check-System", command="uptime")
  .add_validation_step(name="Validate-Profile", data_key="user_data")
  .build()
)
```

---

## Enhanced Features

- **Decorator-based step registration**: Use `@step` for automatic discovery
- **Pre-built templates**: APIAuthStep, APIGetStep, CLIStep, ValidationStep
- **Fluent builder pattern**: Compose workflows with chained methods
- **Rich step results**: Metrics, tags, metadata, expandable data
- **Backward compatibility**: Legacy workflows still supported

---

## Metrics & Tags

- Every step can emit metrics (`add_metric(key, value)`) and tags (`add_tag(tag)`) for reporting and filtering
- Metrics and tags are visible in API, UI, and CLI outputs
- Use metrics for performance, validation, and diagnostics
- Use tags for categorization, filtering, and reporting

---

## Troubleshooting & FAQ

**Common Issues:**
- Import errors: Ensure PYTHONPATH includes project root (use start_services.sh)
- Missing dependencies: Install both requirements files
- Service not starting: Check logs in `valiant/ui/logs/`
- CLI prompts for input: Use `--set` to provide all required context
- API returns empty metrics/tags: Ensure workflow steps use EnhancedStepResult and add metrics/tags

**FAQ:**
- **Q:** Can I use legacy workflows? **A:** Yes, full backward compatibility is maintained
- **Q:** How do I add a new step type? **A:** Subclass StepTemplate and register via add_template()
- **Q:** How do I debug step failures? **A:** Check logs, enable verbose output, inspect metrics/tags

---

## Support & Contribution

- For questions, open an issue or discussion on GitHub
- See [WORKFLOW_DEVELOPMENT_GUIDE.md](WORKFLOW_DEVELOPMENT_GUIDE.md) for advanced developer docs
- Contributions welcome: fork, branch, PR with clear description

---

**Valiant Workflow Automation Platform** — Enterprise-ready, extensible, and developer-friendly

---
  requirements-ui.txt# UI dependencies (Streamlit, FastAPI)
  run.py            # CLI entry point
```

---

## How to Add a Workflow

1. Create a new Python file in `valiant/workflows/`.
2. Subclass `BaseWorkflow` and implement:
   - `get_input_fields()`
   - `define_steps()`
   - Step functions returning `(success, message, data)`
3. Register your workflow in the API/UI if needed.

---

## CLI Usage

Run workflows from command line:
```bash
python run.py run <workflow_name>
```

Available workflows: `api`, `system`, `user`

### Enhanced Workflow Features (NEW!)

The framework now supports **decorator-based workflows** and **pre-built templates** for faster development:

```python
from valiant.framework.enhanced_workflow import EnhancedBaseWorkflow
from valiant.framework.decorators import step, APIAuthStep

class MyWorkflow(EnhancedBaseWorkflow):
    def __init__(self, runner=None):
        super().__init__(runner)
        # Add pre-built authentication step
        self.add_template(APIAuthStep(name="Login", url="/auth/login"))
    
    @step(name="Process-Data", order=2)
    def process_data(self, context):
        return EnhancedStepResult.success("Data processed!")
```

**Key Benefits:**
- 🎯 **70-80% less boilerplate code**
- 🚀 **Pre-built templates** for common patterns (API auth, CLI commands, validation)
- 🔍 **Automatic step discovery** via decorators
- 📝 **Enhanced error handling** and result types
- 🔄 **100% backward compatible** with existing workflows

See the [Workflow Development Guide](WORKFLOW_DEVELOPMENT_GUIDE.md) for complete documentation.

## Example Workflow Step

```python
def step_check_api(self, context: dict) -> tuple:
    response = ... # your logic
    return True, "API check passed", {"response": response}
```

## Service Management Script

The startup script provides convenient commands to manage both UI services:

```bash
cd valiant/ui
bash start_services.sh start    # Start both services
bash start_services.sh stop     # Stop both services  
bash start_services.sh restart  # Restart both services
bash start_services.sh status   # Check service status
bash start_services.sh logs fastapi    # View FastAPI logs
bash start_services.sh logs streamlit  # View Streamlit logs
bash start_services.sh clean    # Clean log and PID files
```

The script automatically sets the correct PYTHONPATH and handles service management with proper logging.

## Troubleshooting

If you encounter import errors when starting services:
- Ensure you're running the start script from the project root
- The script automatically sets PYTHONPATH to include the project root
- Make sure both requirements.txt and requirements-ui.txt are installed
- Check the log files in `valiant/ui/logs/` for detailed error messages
