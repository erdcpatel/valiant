# Valiant Workflow Development Guide

## 🚀 **Unified Framework Architecture**

The Valiant workflow framework features a **streamlined unified architecture** designed for simplicity and developer productivity. Create powerful workflows with minimal code using our single `Workflow` base class and decorator-based step system.

---

## 📋 **Table of Contents**

1. [Quick Start](#quick-start)
2. [Unified Workflow Pattern](#unified-workflow-pattern)
3. [Step Registration and Execution](#step-registration-and-execution)
4. [Input Field Definitions](#input-field-definitions)
5. [Result Handling](#result-handling)
6. [Best Practices](#best-practices)
7. [Migration from Legacy Frameworks](#migration-from-legacy-frameworks)
8. [API Reference](#api-reference)

---

## 🎯 **Quick Start**

### Creating a Simple Workflow

```python
from valiant import Workflow, step, workflow, InputField, InputType

@workflow(name="hello_workflow")
class HelloWorkflow(Workflow):
    def get_input_fields(self):
        return [
            InputField(
                name="username",
                type=InputType.TEXT,
                label="Username",
                help_text="Your name for the greeting"
            )
        ]
    
    @step(name="Greet-User", order=1)
    def greet_user(self, context):
        username = context.get("username", "World")
        message = f"Hello, {username}!"
        
        return self.success(
            message=message,
            data={"greeting": message}
        )
```

### Running Your Workflow

```bash
# CLI execution
python run.py run hello_workflow --set username="Alice"

# Register in config.py
WORKFLOWS = {
    "hello_workflow": "valiant.workflows.hello_workflow.HelloWorkflow"
}
```
---

## 🔧 **Unified Workflow Pattern**

### Single Import Strategy

All workflow components are available through a single import:

```python
from valiant import Workflow, step, workflow, InputField, InputType
```

### Decorator-Based Step Registration

Steps are automatically discovered and registered using the `@step` decorator:

```python
@workflow(name="user_management")
class UserManagementWorkflow(Workflow):
    def get_input_fields(self):
        return [
            InputField(name="username", type=InputType.TEXT, required=True),
            InputField(name="action", type=InputType.SELECT, 
                      options=["create", "update", "delete"], required=True)
        ]
    
    @step(name="Validate-Input", order=1)
    def validate_input(self, context):
        username = context.get("username")
        if not username or len(username) < 3:
            return self.failure("Username must be at least 3 characters")
        return self.success("Input validation passed")
    
    @step(name="Process-User", order=2)
    def process_user(self, context):
        action = context.get("action")
        username = context.get("username")
        
        result = f"Successfully {action}d user {username}"
        return self.success(result, data={"processed_user": username})
```

### Automatic Step Discovery

Steps are automatically discovered and registered based on decorators:

```python
class AutoDiscoveryWorkflow(Workflow):
    @step(order=1)
    def first_step(self, context):
        return self.success("First step complete")
    
    @step(order=2, parallel_group="parallel")
    def second_step(self, context):
        return self.success("Second step complete")
    
    @step(order=2, parallel_group="parallel")
    def third_step(self, context):
        return self.success("Third step complete")
    
    # No manual step registration needed!
```

---

## 📋 **Step Registration and Execution**

### Step Decorator Parameters

```python
@step(
    name="Custom-Step-Name",      # Optional: defaults to method name
    order=1,                      # Execution order
    timeout=60,                   # Step timeout in seconds
    retries=3,                    # Number of retry attempts
    parallel_group="group_name",  # Parallel execution group
    requires=["step1", "step2"],  # Required step dependencies
    description="Step description", # Step description
    tags=["api", "user"],         # Tags for categorization
    enabled=True,                 # Enable/disable step
    skip_on_failure=False         # Skip if previous steps failed
)
def my_step(self, context: Dict) -> StepResult:
    # Step implementation
    return self.success("Step completed")
```

### Result Handling

The unified framework provides simple result methods:

```python
@step(name="Example-Step", order=1)
def example_step(self, context):
    try:
        # Your logic here
        data = process_something(context)
        
        # Success result with metrics and tags
        result = self.success(
            message="Operation completed successfully",
            data={"processed_items": len(data)},
            tags=["processing", "success"],
            metrics={"duration": 2.5, "items_count": len(data)}
        )
        return result
        
    except ValidationError as e:
        return self.failure(f"Validation failed: {str(e)}")
    
    except Exception as e:
        return self.failure(f"Unexpected error: {str(e)}")
```

---

## 📝 **Input Field Definitions**

### Rich Input Field Types

```python
def get_input_fields(self):
    return [
        # Text input with validation
        InputField(
            name="username",
            type=InputType.TEXT,
            label="Username",
            help_text="Enter your username",
            required=True,
            validation_regex=r"^[a-zA-Z0-9_]{3,20}$",
            validation_message="Username must be 3-20 alphanumeric characters"
        ),
        
        # Password input
        InputField(
            name="password",
            type=InputType.PASSWORD,
            label="Password",
            help_text="Enter your password",
            required=True
        ),
        
        # Number input with constraints
        InputField(
            name="timeout",
            type=InputType.NUMBER,
            label="Timeout (seconds)",
            default=30,
            min_value=1,
            max_value=300,
            help_text="Request timeout in seconds"
        ),
        
        # Select dropdown
        InputField(
            name="environment",
            type=InputType.SELECT,
            label="Environment",
            options=["dev", "staging", "prod"],
            default="dev",
            help_text="Target environment",
            required=True
        ),
        
        # Checkbox
        InputField(
            name="enable_logging",
            type=InputType.CHECKBOX,
            label="Enable Detailed Logging",
            default=False,
            help_text="Enable verbose logging output"
        )
    ]
```

---

## ✅ **Result Handling**

### Step Result Methods

The unified framework provides three main result types:

```python
# Success result
return self.success(
    message="Operation completed successfully",
    data={"processed_items": 42},
    metrics={"duration": 2.5, "items_processed": 42},
    tags=["processing", "success"]
)

# Failure result
return self.failure("Operation failed: invalid input")

# Skip result
return self.skip("Skipping due to condition not met")
```

### Metrics and Tags

Add rich metadata to your step results:

```python
@step(name="Process-Data", order=1)
def process_data(self, context):
    start_time = time.time()
    
    try:
        # Process data
        items = process_items(context.get("data", []))
        duration = time.time() - start_time
        
        result = self.success(
            message=f"Processed {len(items)} items successfully",
            data={"processed_items": items}
        )
        
        # Add metrics and tags
        result.add_metric("processing_duration", duration)
        result.add_metric("items_processed", len(items))
        result.add_tag("data-processing")
        result.add_tag("batch-operation")
        
        return result
        
    except Exception as e:
        return self.failure(f"Processing failed: {str(e)}")
```

---

## 💡 **Best Practices**

### 1. Use Descriptive Step Names

```python
# Good
@step(name="Authenticate-User", order=1)
def authenticate_user(self, context):
    pass

# Avoid
@step(name="Step1", order=1)
def step1(self, context):
    pass
```

### 2. Organize Steps with Order and Groups

```python
# Sequential steps
@step(order=1)
def initialize(self, context):
    return self.success("Initialization complete")

@step(order=2)
def authenticate(self, context):
    return self.success("Authentication complete")

# Parallel steps
@step(order=3, parallel_group="data_fetch")
def get_profile(self, context):
    return self.success("Profile retrieved")

@step(order=3, parallel_group="data_fetch")
def get_settings(self, context):
    return self.success("Settings retrieved")

# Final step
@step(order=4)
def generate_report(self, context):
    return self.success("Report generated")
```

### 3. Handle Errors Gracefully

```python
@step(name="Safe-Operation", retries=3, timeout=30)
def safe_operation(self, context):
    try:
        # Operation that might fail
        result = risky_operation()
        
        return self.success(
            message="Operation completed successfully",
            data=result,
            metrics={"attempts": 1}
        )
        
    except SpecificException as e:
        return self.failure(f"Known error occurred: {str(e)}")
        
    except Exception as e:
        return self.failure(f"Unexpected error: {str(e)}")
```

### 4. Use Context for Data Flow

```python
@step(name="Fetch-Data", order=1)
def fetch_data(self, context):
    data = fetch_from_api()
    context["fetched_data"] = data
    return self.success("Data fetched successfully")

@step(name="Process-Data", order=2)
def process_data(self, context):
    data = context.get("fetched_data")
    if not data:
        return self.failure("No data to process")
    
    processed = process(data)
    context["processed_data"] = processed
    return self.success("Data processed successfully")
```

### 5. Add Comprehensive Documentation

```python
@workflow(name="documented_workflow")
class DocumentedWorkflow(Workflow):
    """
    Comprehensive workflow for user account management and validation.
    
    This workflow performs:
    1. Input validation
    2. User account processing
    3. Result verification
    """
    
    def get_input_fields(self):
        return [
            InputField(
                name="username",
                type=InputType.TEXT,
                label="Username",
                help_text="User account name (3-20 characters)",
                required=True
            )
        ]
    
    @step(
        name="Validate-User-Account",
        order=1,
        description="Validates user account status and permissions",
        tags=["validation", "security"]
    )
    def validate_user(self, context):
        """Validate user account before processing."""
        username = context.get("username")
        
        if not username:
            return self.failure("Username is required")
            
        return self.success("User validation complete")
```

---

## 🔄 **Migration from Legacy Frameworks**

### Step 1: Update Imports

```python
# Before (if migrating from legacy systems)
from some.legacy.framework import LegacyWorkflow

# After
from valiant import Workflow, step, workflow, InputField, InputType
```

### Step 2: Convert Base Class

```python
# Before (legacy pattern)
class MyWorkflow(LegacyWorkflow):
    def get_steps(self):
        return [...]

# After  
@workflow(name="my_workflow")
class MyWorkflow(Workflow):
    def get_input_fields(self):
        return [...]
```

### Step 3: Update Step Results

```python
# Before (legacy tuple returns)
def step_one(self, context):
    return True, "Completed", {"data": "value"}

# After
def step_one(self, context):
    return self.success("Completed", data={"data": "value"})
```

### Step 4: Use Decorator Registration

```python
# Before - Manual registration
def register_steps(self):
    self.add_step("Step1", self.step_one)

# After - Automatic with decorators
@step(order=1)
def step_one(self, context):
    return self.success("Step completed")
```

---

## 📚 **API Reference**

### Core Classes

- `Workflow`: Unified base class for all workflows
- `InputField`: Input field definition with validation
- `InputType`: Enum for input field types

### Decorators

- `@workflow(name)`: Register workflow class
- `@step()`: Register method as workflow step
  - Parameters: `name`, `order`, `timeout`, `retries`, `parallel_group`, `requires`, `description`, `tags`, `enabled`

### Result Methods

- `self.success(message, data=None, tags=None, metrics=None)`: Return success result
- `self.failure(message)`: Return failure result  
- `self.skip(message)`: Return skip result

### Input Types

- `InputType.TEXT`: Text input
- `InputType.PASSWORD`: Password input
- `InputType.NUMBER`: Numeric input
- `InputType.SELECT`: Dropdown selection
- `InputType.CHECKBOX`: Checkbox input
- `InputType.DATE`: Date picker

---

## 🎯 **Examples**

### Complete User Management Workflow

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
                      options=["admin", "user", "guest"], default="user")
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
        role = context.get("role", "user")
        
        if action == "create":
            result = f"Created user {username} with role {role}"
        elif action == "update":
            result = f"Updated user {username}"
        else:
            result = f"Deleted user {username}"
        
        return self.success(
            message=result,
            data={"processed_user": username, "action": action},
            tags=["user-management", action],
            metrics={"processing_time": 1.2}
        )
```

See the complete examples in:
- `valiant/workflows/demo.py` - Simple demonstration workflow
- `valiant/workflows/user_management.py` - Complete user management workflow

---

## 🆘 **Support**

For questions or issues:
1. Check existing workflow examples in `valiant/workflows/`
2. Review this documentation
3. Test your workflow using the CLI: `python run.py run <workflow_name>`
4. Check service logs in `valiant/ui/logs/` for debugging

---

**Happy workflow building! 🚀**
