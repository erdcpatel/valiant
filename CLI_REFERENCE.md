# Valiant CLI Reference Guide

## Available Commands

The Valiant CLI provides three main commands for workflow management:

### 🚀 `create` - Generate Workflows from Templates

Create new workflows using intelligent templates that generate complete code, tests, and documentation.

```bash
python run.py create [TEMPLATE_NAME] [OPTIONS]
```

**Options:**
- `TEMPLATE_NAME` - Template to use (optional, shows selection if omitted)
- `--output, -o DIRECTORY` - Output directory for generated files (default: current directory)
- `--interactive/--non-interactive` - Interactive mode (default: interactive)
- `--help` - Show command help

**Examples:**
```bash
# Interactive template selection
python run.py create

# Generate API+DB integration workflow
python run.py create api_db_integration

# Generate to custom directory
python run.py create api_db_integration --output ./my_workflows/

# Non-interactive mode (uses defaults)
python run.py create api_db_integration --non-interactive

# Show help
python run.py create --help
```

**Available Templates:**
- `api_db_integration` - REST API integration with Trino database operations

**What Gets Generated:**
- Complete workflow Python file with steps and error handling
- Unit test suite with comprehensive mocking
- Markdown documentation with usage examples
- Enterprise patterns (authentication, validation, monitoring)

---

### ▶️ `run` - Execute Workflows

Run existing workflows with parameters and configuration options.

```bash
python run.py run WORKFLOW_NAME [OPTIONS]
```

**Options:**
- `WORKFLOW_NAME` - Name of workflow to execute (required)
- `--verbose, -v` - Enable verbose output for debugging
- `--timeout SECONDS` - Default timeout per step (default: 30.0)
- `--retries NUMBER` - Number of retries for failed steps (default: 1)
- `--output FORMAT` - Output format: `rich` or `json` (default: rich)
- `--save-context` - Save context to context.json file
- `--set KEY=VALUE` - Set manual context values (can be used multiple times)
- `--env ENVIRONMENT` - Environment to load configuration for (dev, prod, test)
- `--config-dir PATH` - Configuration directory path (default: config)
- `--help` - Show command help

**Examples:**
```bash
# Interactive execution (prompts for inputs)
python run.py run demo

# Provide parameters via command line
python run.py run demo --set user_name="Alice" --set user_email="alice@example.com"

# Multiple parameters
python run.py run user_management \
  --set username=john \
  --set email=john@example.com \
  --set action=create \
  --set role=admin

# Verbose output for debugging
python run.py run demo --verbose --set user_name="Test"

# JSON output format
python run.py run demo --output json --set user_name="Test"

# Custom timeout and retries
python run.py run demo --timeout 60 --retries 3 --set user_name="Test"

# Load specific environment config
python run.py run demo --env prod --set user_name="Test"

# Save execution context
python run.py run demo --save-context --set user_name="Test"
```

**Parameter Types:**
- **Text**: `--set username="john"`
- **Email**: `--set email="john@example.com"`
- **Numbers**: `--set max_items=10`
- **Selections**: `--set action=create` (must match defined options)

---

### 📋 `list` - Show Available Workflows

Display all registered workflows in the system.

```bash
python run.py list [OPTIONS]
```

**Options:**
- `--output FORMAT` - Output format: `rich` or `json` (default: rich)
- `--help` - Show command help

**Examples:**
```bash
# Rich table format (default)
python run.py list

# JSON format for programmatic use
python run.py list --output json
```

**Sample Output:**
```
                             Available Workflows                              
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name            ┃ Class Path                                               ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ demo            │ valiant.workflows.demo.DemoWorkflow                      │
│ user_management │ valiant.workflows.user_management.UserManagementWorkflow │
└─────────────────┴──────────────────────────────────────────────────────────┘
```

---

## Global Options

**Completion Support:**
```bash
# Install shell completion
python run.py --install-completion

# Show completion script
python run.py --show-completion

# Help
python run.py --help
```

---

## Common Workflows

### 1. Quick Workflow Development
```bash
# Generate workflow from template
python run.py create api_db_integration

# Test the generated workflow
python run.py run my_api_workflow --set api_key="test_key"
```

### 2. Production Workflow Execution
```bash
# Run with production config and comprehensive logging
python run.py run data_sync \
  --env prod \
  --verbose \
  --timeout 300 \
  --retries 3 \
  --save-context \
  --set batch_size=5000 \
  --set api_endpoint="https://api.company.com/data"
```

### 3. Development and Testing
```bash
# List available workflows
python run.py list

# Run with debug output
python run.py run demo --verbose --output json --set user_name="Debug"

# Quick test with minimal data
python run.py run user_management \
  --set username=testuser \
  --set email=test@test.com \
  --set action=create \
  --set role=user
```

### 4. CI/CD Integration
```bash
# Non-interactive execution for automation
python run.py run data_pipeline \
  --output json \
  --set source_url="${SOURCE_URL}" \
  --set target_table="${TARGET_TABLE}" \
  --set batch_size=1000 \
  --env "${ENVIRONMENT}"
```

---

## Output Formats

### Rich Format (Default)
- Colored, formatted tables
- Progress indicators
- Rich error messages
- Interactive experience

### JSON Format
- Machine-readable output
- Perfect for automation
- Includes all metrics and metadata
- CI/CD friendly

**JSON Structure:**
```json
{
  "steps": [
    {
      "name": "Step Name",
      "success": true,
      "message": "Step completed successfully",
      "time_taken": 1.23,
      "derived_metrics": {"items_processed": 100},
      "tags": ["processing", "success"]
    }
  ],
  "summary": {
    "total_steps": 3,
    "successful_steps": 3,
    "total_time": 4.56
  }
}
```

---

## Error Handling

**Common Exit Codes:**
- `0` - Success
- `1` - Workflow execution failure or validation error
- `2` - Invalid command or missing arguments

**Troubleshooting:**
```bash
# Verbose output for debugging
python run.py run workflow_name --verbose

# Check available workflows
python run.py list

# Validate template system
python run.py create --help

# Check workflow help
python run.py run --help
```

---

## Environment Configuration

Use `--env` to load environment-specific settings:

```bash
# Development environment
python run.py run workflow --env dev

# Production environment  
python run.py run workflow --env prod

# Test environment
python run.py run workflow --env test
```

Configuration files: `valiant/config/application-{env}.yaml`

---

*For more details, see [README.md](README.md) and [TEMPLATE_SYSTEM_README.md](TEMPLATE_SYSTEM_README.md)*