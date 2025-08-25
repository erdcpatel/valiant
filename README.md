# Valiant Workflow Automation

Valiant is a generic, extensible tool to automate and orchestrate validation workflows. It allows you to define, configure, and execute a series of validation steps for any system or API, with a modern UI and API for both technical and non-technical users.

---

## Features

- **Dynamic Workflow Engine:** Define workflows as Python classes with step functions.
- **Flexible Input Schema:** Supports text, password, number, select/dropdown, date, and checkbox/boolean fields.
- **Modern UI:** Streamlit-based web UI for running workflows and viewing results.
- **REST API:** FastAPI backend for programmatic workflow execution and integration.
- **Step Results Table:** Compact, user-friendly results table with expandable JSON data per step.
- **Service Management:** Shell script to start/stop/restart/status both UI and API services.
- **Logging:** Per-service log files for troubleshooting.
- **Extensible:** Add new workflows by subclassing `BaseWorkflow`.

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/valiant.git
cd valiant
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Start the Services

```bash
cd valiant/ui
bash start_services.sh start
```

- **Streamlit UI:** [http://localhost:8501](http://localhost:8501)
- **FastAPI:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Stop the Services

```bash
bash start_services.sh stop
```

---

## Directory Structure

```
valiant/
  framework/         # Core engine, workflow base classes
  workflows/         # Example and custom workflows
  ui/
    streamlit_app.py # Streamlit UI
    fastapi_app.py   # FastAPI backend
    start_services.sh# Service management script
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

## Example Workflow Step

```python
def step_check_api(self, context: dict) -> tuple:
    response = ... # your logic
    return True, "API check passed", {"response": response}
```
