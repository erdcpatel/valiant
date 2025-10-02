# Valiant Workflow Templates 🚀

## Smart Workflow Code Generation System

The Valiant Template System eliminates the "blank page problem" by providing intelligent workflow code generation. Instead of starting from scratch, developers answer a few questions and get complete, production-ready workflow code with tests and documentation.

## Features

✅ **Question-Driven Generation**: Interactive prompts gather workflow requirements  
✅ **Complete Code Output**: Generates workflow, tests, and documentation  
✅ **Enterprise Patterns**: Built-in best practices for API integration and database operations  
✅ **Type Safety**: Full type hints and validation built-in  
✅ **Zero Framework Changes**: 100% additive - existing workflows unaffected  

## Available Templates

### 🔗 API + Database Integration (`api_db_integration`)

Perfect for workflows that integrate REST APIs with Trino databases. Generates code for:

- **API Operations**: Fetch data with authentication (API key, Bearer token, Basic auth)
- **Data Validation**: Pandas-based validation with error reporting
- **Database Operations**: Trino integration with batch processing
- **Error Handling**: Retry logic, error logging, and recovery strategies
- **Testing**: Complete unit test suite with mocking
- **Documentation**: Comprehensive markdown documentation

**Generated Files:**
- `{workflow_name}.py` - Main workflow implementation
- `test_{workflow_name}.py` - Unit test suite
- `{workflow_name}.md` - Complete documentation

## Quick Start

### 1. Interactive Template Creation

```bash
# Launch interactive template selection
python run.py create

# Or specify template directly
python run.py create api_db_integration
```

### 2. Answer Configuration Questions

The template engine will guide you through configuration:

```
✨ Creating workflow from template: api_db_integration

What should we call this workflow? User Data Sync
Brief description? Synchronize user data from API to database
What's the base URL of the API? https://api.company.com
Which API endpoints will you use? GET /users, POST /users
What authentication does the API use? api_key
Trino database host? trino.company.com:443
Trino catalog to use? hive
Target table name? user_sync_table
What operations should this workflow perform? fetch_api_data, validate_data, insert_to_db
```

### 3. Generated Workflow Example

The template generates a complete workflow like this:

```python
@workflow("user_data_sync")
class UserDataSyncWorkflow(Workflow):
    def inputs(self):
        return [
            InputField("api_key", type="password", required=True),
            InputField("batch_size", type="number", default=1000),
        ]
    
    @step("Fetch API Data", order=1, tags=["api", "fetch"])
    def fetch_api_data(self, context: Dict):
        # Complete implementation with error handling
        headers = self._get_auth_headers(context)
        response = requests.get(f"{context['api_base_url']}/users", headers=headers)
        # ... full implementation
    
    @step("Validate Data", order=2, tags=["validation"])
    def validate_data(self, context: Dict):
        # Pandas-based validation logic
        # ... complete validation implementation
    
    @step("Insert to Database", order=3, tags=["database"])
    def insert_to_database(self, context: Dict):
        # Trino batch insert with connection management
        # ... full database integration
```

### 4. Run Generated Workflow

```bash
python run.py run user_data_sync --set api_key="your_key" --set batch_size=500
```

## Template System Architecture

### Template Engine (`valiant/templates/engine.py`)

- **Question System**: Declarative question definitions with validation
- **Code Generation**: Template-based code generation with context substitution  
- **File Management**: Multiple file type support (workflow, test, documentation)
- **Interactive Mode**: CLI-friendly question prompts with rich formatting

### Template Implementation (`valiant/templates/api_db_template.py`)

- **Configuration Questions**: Comprehensive API and database configuration
- **Code Generation**: Generates step methods, helper functions, and imports
- **Best Practices**: Enterprise patterns for error handling and monitoring
- **Documentation**: Auto-generated markdown with usage examples

## Development Productivity Impact

### Before Templates (Traditional Approach)
```
1. Research framework patterns          30-60 minutes
2. Write workflow structure            20-30 minutes  
3. Implement step methods              60-90 minutes
4. Add error handling                  30-45 minutes
5. Write unit tests                    45-60 minutes
6. Create documentation                20-30 minutes
Total: 3.5-5 hours for basic workflow
```

### After Templates (Smart Generation)
```
1. Run template command                1 minute
2. Answer configuration questions      5-10 minutes
3. Review and customize generated code 15-30 minutes
Total: 20-40 minutes for complete workflow
```

**Productivity Gain: 85-90% time reduction**

## Risk Assessment ✅

### Zero Breaking Changes
- **Additive Design**: Templates live in separate `valiant/templates/` module
- **No Framework Changes**: Core workflow engine untouched
- **Backward Compatibility**: All existing workflows continue working unchanged
- **Optional Feature**: Teams can adopt gradually or ignore completely

### Safe Implementation
- **Isolated Code**: Template system isolated from core framework
- **Validation**: Input validation prevents invalid code generation
- **Testing**: Generated code includes comprehensive unit tests
- **Documentation**: Every generated workflow includes full documentation

## CLI Commands

### Create Workflow from Template
```bash
# Interactive mode - shows available templates
python run.py create

# Specify template directly
python run.py create api_db_integration

# Custom output directory
python run.py create api_db_integration --output ./my_workflows/

# Non-interactive mode (requires all template defaults)
python run.py create api_db_integration --non-interactive
```

### List Available Templates
```bash
python run.py templates list
```

## Template Customization

Templates are Python classes that extend `WorkflowTemplate`. Each template defines:

1. **Questions**: Configuration questions with types and validation
2. **Generation Logic**: Code generation based on user answers
3. **File Templates**: Python code templates with variable substitution

### Adding New Templates

```python
# valiant/templates/my_template.py
class MyTemplate(WorkflowTemplate):
    def _setup_questions(self):
        self.add_question("workflow_name", "Workflow name?", QuestionType.TEXT)
        # Add more questions...
    
    def _generate_files(self, answers):
        # Generate workflow files based on answers
        return [GeneratedFile(...)]
```

Register in `valiant/templates/__init__.py`:
```python
from .my_template import MyTemplate
```

## Integration with Framework

The template system integrates seamlessly with existing Valiant features:

- **CLI Integration**: `run.py create` command
- **Workflow Registry**: Generated workflows auto-discoverable  
- **Engine Compatibility**: Generated code uses existing workflow patterns
- **UI Support**: Generated workflows work in FastAPI and Streamlit UIs

## Examples

### API Integration Template Output

See sample files:
- [`sample_api_db_workflow.py`](./sample_api_db_workflow.py) - Generated workflow code
- [`sample_api_db_workflow.md`](./sample_api_db_workflow.md) - Generated documentation

## Benefits Summary

🎯 **Developer Experience**
- Eliminate blank page paralysis
- Reduce time-to-first-workflow by 85%+
- Built-in best practices and patterns
- Complete code with tests and docs

⚡ **Team Velocity**  
- Faster workflow development
- Consistent code patterns across team
- Reduced learning curve for new developers
- Focus on business logic vs. boilerplate

🛡️ **Quality & Safety**
- Zero impact on existing workflows
- Generated code includes comprehensive tests
- Built-in error handling and monitoring
- Enterprise-grade patterns by default

🔧 **Extensibility**
- Easy to add new templates
- Template system is pluggable
- Customizable code generation
- Framework remains flexible

---

The Template System transforms Valiant from a workflow framework into an **intelligent workflow development platform** that accelerates team productivity while maintaining code quality and safety.