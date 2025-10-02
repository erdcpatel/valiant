
# Valiant Workflow Automation Platform

Valiant is a **streamlined Python workflow automation platform** designed for simplicity and developer productivity. Create powerful workflows with minimal code using our unified architecture and decorator-based step system.

---

## Requirements & Environment

- **Python**: 3.10+ recommended (tested on 3.10, 3.11, 3.12, 3.13)
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

## Quick Start

### Option 1: Create Workflow from Template (Recommended) 🚀

**NEW**: Use our Smart Template System to generate complete workflows in minutes:

```bash
# Interactive template creation
python run.py create

# Or specify template directly
python run.py create api_db_integration
```

**What you get:** Complete workflow code, unit tests, and documentation generated from a few questions!

### Option 2: Create Your First Workflow Manually
```python
from valiant import Workflow, step, InputField, InputType

@workflow(name="my_workflow")
class MyWorkflow(Workflow):
    def get_input_fields(self):
        return [
            InputField(name="username", type=InputType.TEXT, required=True),
            InputField(name="action", type=InputType.TEXT, required=True)
        ]
    
    @step(name="Process-User", order=1)
    def process_user(self, context):
        username = context.get("username")
        action = context.get("action")
        
        # Your workflow logic here
        return self.success(f"Processed {action} for {username}")
```

### Run Your Workflow
```bash
python run.py run my_workflow --set username=alice --set action=create
```

---

## Service Management

The `start_services.sh` script manages both UI and API services:
```bash
cd valiant/ui
bash start_services.sh start      # Start both services (FastAPI + Streamlit)
bash start_services.sh stop       # Stop both services
bash start_services.sh restart    # Restart both services
bash start_services.sh status     # Check service status
bash start_services.sh logs fastapi    # View FastAPI logs
bash start_services.sh logs streamlit  # View Streamlit logs
bash start_services.sh clean      # Clean log and PID files
```

**Services:**
- **FastAPI**: `http://localhost:8000` - REST API for workflow execution
- **Streamlit**: `http://localhost:8501` - Web UI for interactive workflow management

---

## Workflow Development

### Unified Architecture - Simple and Clean

Valiant uses a **single `Workflow` base class** with decorator-based step registration:

```python
from valiant import Workflow, step, workflow, InputField, InputType

@workflow(name="user_management")
class UserManagementWorkflow(Workflow):
    def get_input_fields(self):
        return [
            InputField(name="username", type=InputType.TEXT, required=True),
            InputField(name="email", type=InputType.TEXT, required=True),
            InputField(name="action", type=InputType.SELECT, 
                      options=["create", "update", "delete"], required=True),
            InputField(name="role", type=InputType.SELECT, 
                      options=["admin", "user", "guest"], required=True)
        ]
    
    @step(name="Validate-Input", order=1)
    def validate_input(self, context):
        username = context.get("username")
        email = context.get("email")
        
        if not username or len(username) < 3:
            return self.failure("Username must be at least 3 characters")
        
        if "@" not in email:
            return self.failure("Invalid email format")
            
        return self.success("Input validation passed")
    
    @step(name="Process-User", order=2)
    def process_user(self, context):
        action = context.get("action")
        username = context.get("username")
        
        # Your business logic here
        if action == "create":
            result = f"Created user {username}"
        elif action == "update":
            result = f"Updated user {username}"
        else:
            result = f"Deleted user {username}"
            
        return self.success(result, data={"processed_user": username})
```

### Key Features

- **🎯 Single Import**: `from valiant import Workflow, step, workflow`
- **🚀 Decorator-Based**: Use `@step` for automatic step registration
- **📝 Rich Results**: Built-in `success()`, `failure()`, `skip()` methods
- **🔧 Input Validation**: Type-safe input fields with validation
- **📊 Metrics & Tags**: Add metrics and tags for reporting
- **🔄 Auto-Discovery**: Workflows are automatically discovered and registered

---

## CLI Usage

### Smart Workflow Templates ✨

**NEW**: Generate complete workflows with our template system:

```bash
# Create workflow from template (interactive)
python run.py create                                 # Shows available templates
python run.py create api_db_integration              # Create API+DB workflow
python run.py create api_db_integration --output ./my_workflows/  # Custom directory

# What you get:
# ✅ Complete workflow with enterprise patterns
# ✅ Unit tests with mocking  
# ✅ Comprehensive documentation
# ✅ 85% faster than manual creation
```

**Available Templates:**
- `api_db_integration` - REST API integration with Trino database operations

### Run Existing Workflows

Run workflows from command line:
```bash
python run.py run <workflow_name>                    # Interactive mode
python run.py run <workflow_name> --set key=value   # Provide parameters
python run.py list                                  # List available workflows
```

Available workflows: `demo`, `user_management`

### Example Commands
```bash
# Run demo workflow with parameters
python run.py run demo --set user_name="Alice" --set user_email="alice@example.com"

# Run user management workflow
python run.py run user_management --set username=john --set email=john@example.com --set action=create --set role=user
```

---

## Step Results and Error Handling

```python
@step(name="Example-Step", order=1)
def example_step(self, context):
    try:
        # Your logic here
        result = process_data(context)
        
        # Success with data and metrics
        return self.success(
            message="Data processed successfully",
            data={"processed_items": len(result)},
            tags=["processing", "success"],
            metrics={"duration": 2.5, "items_count": len(result)}
        )
        
    except ValidationError as e:
        return self.failure(f"Validation failed: {str(e)}")
    
    except Exception as e:
        return self.failure(f"Unexpected error: {str(e)}")
```

---

## API Endpoints

- **FastAPI Server**: `http://localhost:8000`
  - `GET /workflows` - List available workflows
  - `POST /run/{workflow_name}` - Execute workflow with JSON payload
  - `GET /health` - Health check endpoint

### Example API Usage
```bash
curl -X POST http://localhost:8000/run/user_management \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "action": "create",
    "role": "admin"
  }'
```

---

## Troubleshooting

**Common Issues:**
- **Import errors**: Ensure PYTHONPATH includes project root (use start_services.sh)
- **Missing dependencies**: Install both requirements files
- **Service not starting**: Check logs in `valiant/ui/logs/`
- **CLI prompts for input**: Use `--set` to provide all required parameters
- **Workflow not found**: Check workflow registration in `valiant/workflows/config.py`

**Environment Setup:**
```bash
# Check your Python version
python --version

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-ui.txt

# Test CLI
python run.py list
```

---

## Project Structure

```
valiant/
├── framework/           # Core workflow engine
├── workflows/           # Workflow implementations
│   ├── config.py       # Workflow registry
│   ├── demo.py         # Demo workflow
│   └── user_management.py
├── ui/                 # Web interfaces
│   ├── fastapi_app.py  # REST API
│   ├── streamlit_app.py # Web UI
│   └── start_services.sh
└── config/             # Configuration files
```

---

## Support & Contribution

- **📚 Documentation**: See [TEMPLATE_SYSTEM_README.md](TEMPLATE_SYSTEM_README.md) for template system docs
- **🛠️ Advanced Development**: See [WORKFLOW_DEVELOPMENT_GUIDE.md](WORKFLOW_DEVELOPMENT_GUIDE.md) for detailed developer guide
- **❓ Questions**: Open an issue or discussion on GitHub
- **🤝 Contributions**: Fork, branch, PR with clear description

### Key Features
- **🚀 Smart Templates**: Generate workflows 85% faster with our template system
- **🎯 Simple API**: Single import, decorator-based architecture  
- **🔧 Type Safety**: Input validation and type hints built-in
- **📊 Rich Monitoring**: Metrics, tags, and detailed reporting
- **🌐 Dual UI**: FastAPI REST API + Streamlit web interface

---

**Valiant Workflow Automation Platform** — Simple, powerful, and developer-friendly
