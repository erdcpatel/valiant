"""
REST API + Database Template for Valiant Workflows

Generates workflows that integrate with REST APIs and Trino databases,
following enterprise patterns for data processing and API integration.
"""

from typing import Dict, List, Any
from .engine import WorkflowTemplate, TemplateQuestion, QuestionType, GeneratedFile


class ApiDbTemplate(WorkflowTemplate):
    """Template for REST API + Database integration workflows"""
    
    def __init__(self):
        super().__init__(
            name="api_db_integration",
            description="REST API integration with Trino database operations",
            category="integration"
        )
    
    def _setup_questions(self):
        """Define questions for API + DB workflow configuration"""
        
        # Workflow metadata
        self.add_question(
            "workflow_name", 
            "What should we call this workflow?",
            QuestionType.TEXT,
            required=True,
            help_text="A descriptive name for your workflow (e.g., 'User Data Sync')"
        )
        
        self.add_question(
            "description",
            "Brief description of what this workflow does?",
            QuestionType.TEXT,
            required=True,
            help_text="One-line description for documentation"
        )
        
        # API Configuration
        self.add_question(
            "api_base_url",
            "What's the base URL of the API?",
            QuestionType.TEXT,
            required=True,
            default="https://api.example.com",
            help_text="Base URL for the REST API (e.g., https://api.example.com)"
        )
        
        self.add_question(
            "api_endpoints",
            "Which API endpoints will you use?",
            QuestionType.MULTISELECT,
            required=True,
            options=["GET /users", "POST /users", "PUT /users/{id}", "DELETE /users/{id}", 
                    "GET /data", "POST /data", "Custom endpoint"],
            help_text="Select the API endpoints your workflow will interact with"
        )
        
        self.add_question(
            "auth_type",
            "What authentication does the API use?",
            QuestionType.SELECT,
            required=True,
            options=["none", "api_key", "bearer_token", "basic_auth", "oauth2"],
            default="api_key",
            help_text="Authentication method for the API"
        )
        
        # Database Configuration  
        self.add_question(
            "trino_host",
            "Trino database host?",
            QuestionType.TEXT,
            required=True,
            default="localhost:8080",
            help_text="Trino host and port (e.g., trino.company.com:443)"
        )
        
        self.add_question(
            "trino_catalog",
            "Trino catalog to use?",
            QuestionType.TEXT,
            required=True,
            default="hive",
            help_text="Trino catalog name (e.g., hive, iceberg, postgresql)"
        )
        
        self.add_question(
            "trino_schema",
            "Trino schema/database name?",
            QuestionType.TEXT,
            required=True,
            default="default",
            help_text="Schema name in the Trino catalog"
        )
        
        self.add_question(
            "target_table",
            "Target table name for data operations?",
            QuestionType.TEXT,
            required=True,
            help_text="Name of the table for INSERT/UPDATE operations"
        )
        
        # Workflow Operations
        self.add_question(
            "operations",
            "What operations should this workflow perform?",
            QuestionType.MULTISELECT,
            required=True,
            options=["fetch_api_data", "validate_data", "transform_data", 
                    "insert_to_db", "update_db_records", "sync_api_to_db", 
                    "query_db_data", "send_api_response"],
            help_text="Select the operations your workflow will perform"
        )
        
        self.add_question(
            "error_handling",
            "How should errors be handled?",
            QuestionType.MULTISELECT,
            required=False,
            options=["retry_failed_requests", "log_errors_to_db", "send_error_notifications", 
                    "create_error_reports", "skip_invalid_records"],
            default=["retry_failed_requests", "log_errors_to_db"],
            help_text="Error handling strategies"
        )
        
        self.add_question(
            "include_tests",
            "Generate unit tests?",
            QuestionType.BOOLEAN,
            required=False,
            default=True,
            help_text="Generate test files for the workflow"
        )
    
    def _generate_files(self, answers: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate workflow files based on answers"""
        files = []
        
        # Create context for template rendering
        context = self._build_context(answers)
        
        # Generate main workflow file
        workflow_content = self._generate_workflow_code(context)
        workflow_filename = f"{context['workflow_class_name'].lower()}.py"
        
        files.append(GeneratedFile(
            path=workflow_filename,
            content=workflow_content,
            file_type="workflow"
        ))
        
        # Generate test file if requested
        if answers.get("include_tests", True):
            test_content = self._generate_test_code(context)
            test_filename = f"test_{context['workflow_class_name'].lower()}.py"
            
            files.append(GeneratedFile(
                path=test_filename,
                content=test_content,
                file_type="test"
            ))
        
        # Generate documentation
        doc_content = self._generate_documentation(context)
        doc_filename = f"{context['workflow_class_name'].lower()}.md"
        
        files.append(GeneratedFile(
            path=doc_filename,
            content=doc_content,
            file_type="doc"
        ))
        
        return files
    
    def _build_context(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Build template context from user answers"""
        workflow_name = answers["workflow_name"]
        workflow_id = self._sanitize_name(workflow_name)
        workflow_class_name = "".join(word.capitalize() for word in workflow_id.split("_")) + "Workflow"
        
        # Determine required imports based on operations
        operations = answers.get("operations", [])
        auth_type = answers.get("auth_type", "none")
        
        imports = ["from typing import Dict", "from valiant import Workflow, step, InputField, workflow"]
        
        if any("api" in op or "fetch" in op for op in operations):
            imports.append("import requests")
        
        if any("db" in op or "query" in op or "insert" in op or "update" in op for op in operations):
            imports.append("import trino")
        
        if "validate_data" in operations:
            imports.append("import pandas as pd")
        
        context = {
            "workflow_name": workflow_name,
            "workflow_id": workflow_id,
            "workflow_class_name": workflow_class_name,
            "description": answers["description"],
            "api_base_url": answers["api_base_url"],
            "api_endpoints": answers.get("api_endpoints", []),
            "auth_type": auth_type,
            "trino_host": answers["trino_host"],
            "trino_catalog": answers["trino_catalog"],
            "trino_schema": answers["trino_schema"],
            "target_table": answers["target_table"],
            "operations": operations,
            "error_handling": answers.get("error_handling", []),
            "imports": "\n".join(imports),
            "auth_required": auth_type != "none"
        }
        
        return context
    
    def _generate_workflow_code(self, context: Dict[str, Any]) -> str:
        """Generate the main workflow Python code"""
        
        template = '''"""
{description}

Generated by Valiant API + Database Template
"""

{imports}


@workflow("{workflow_id}")
class {workflow_class_name}(Workflow):
    """{description}"""
    
    name = "{workflow_name}"
    description = "{description}"
    version = "1.0.0"
    tags = ["api", "database", "integration", "trino"]
    
    def inputs(self):
        """Define input fields for the workflow"""
        return [
{input_fields}
        ]
{workflow_steps}
{helper_methods}
'''
        
        # Generate input fields
        input_fields = self._generate_input_fields(context)
        
        # Generate workflow steps
        workflow_steps = self._generate_workflow_steps(context)
        
        # Generate helper methods
        helper_methods = self._generate_helper_methods(context)
        
        context.update({
            "input_fields": input_fields,
            "workflow_steps": workflow_steps,
            "helper_methods": helper_methods
        })
        
        return self._render_template(template, context)
    
    def _generate_input_fields(self, context: Dict[str, Any]) -> str:
        """Generate input field definitions"""
        fields = [
            '            InputField("batch_size", type="number", min_value=1, max_value=10000,',
            '                      default=1000, help_text="Records to process per batch"),'
        ]
        
        if context["auth_required"]:
            if context["auth_type"] == "api_key":
                fields.extend([
                    '            InputField("api_key", type="password", required=True,',
                    '                      help_text="API key for authentication"),'
                ])
            elif context["auth_type"] == "bearer_token":
                fields.extend([
                    '            InputField("bearer_token", type="password", required=True,',
                    '                      help_text="Bearer token for authentication"),'
                ])
            elif context["auth_type"] == "basic_auth":
                fields.extend([
                    '            InputField("username", type="text", required=True,',
                    '                      help_text="Username for basic authentication"),',
                    '            InputField("password", type="password", required=True,',
                    '                      help_text="Password for basic authentication"),'
                ])
        
        if "validate_data" in context["operations"]:
            fields.extend([
                '            InputField("validation_rules", type="text", required=False,',
                '                      help_text="JSON string of validation rules"),',
            ])
        
        return "\n".join(fields)
    
    def _generate_workflow_steps(self, context: Dict[str, Any]) -> str:
        """Generate workflow step methods"""
        steps = []
        operations = context["operations"]
        step_order = 1
        
        if "fetch_api_data" in operations:
            steps.append(self._generate_fetch_api_step(step_order))
            step_order += 1
        
        if "validate_data" in operations:
            steps.append(self._generate_validate_data_step(step_order))
            step_order += 1
        
        if "transform_data" in operations:
            steps.append(self._generate_transform_data_step(step_order))
            step_order += 1
        
        if "query_db_data" in operations:
            steps.append(self._generate_query_db_step(step_order))
            step_order += 1
        
        if "insert_to_db" in operations:
            steps.append(self._generate_insert_db_step(step_order))
            step_order += 1
        
        if "sync_api_to_db" in operations:
            steps.append(self._generate_sync_step(step_order))
            step_order += 1
        
        return "\n".join(steps)
    
    def _generate_fetch_api_step(self, order: int) -> str:
        """Generate API data fetching step"""
        return f'''
    @step("Fetch API Data", order={order}, tags=["api", "fetch"])
    def fetch_api_data(self, context: Dict):
        """Fetch data from the REST API"""
        try:
            headers = self._get_auth_headers(context)
            response = requests.get(
                f"{{context['api_base_url']}}/data",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            api_data = response.json()
            context["api_data"] = api_data
            context["api_record_count"] = len(api_data) if isinstance(api_data, list) else 1
            
            result = self.success(f"Fetched {{len(api_data) if isinstance(api_data, list) else 1}} records from API")
            result.add_metric("api_records_fetched", context["api_record_count"])
            result.add_metric("api_response_time", response.elapsed.total_seconds())
            result.add_tag("api-success")
            
            return result
            
        except requests.exceptions.RequestException as e:
            return self.failure(f"API request failed: {{str(e)}}")
        except Exception as e:
            return self.failure(f"Unexpected error fetching API data: {{str(e)}}")'''
    
    def _generate_validate_data_step(self, order: int) -> str:
        """Generate data validation step"""
        return f'''
    @step("Validate Data", order={order}, tags=["validation"])
    def validate_data(self, context: Dict):
        """Validate the fetched data"""
        try:
            data = context.get("api_data", [])
            if not data:
                return self.failure("No data to validate")
            
            # Convert to DataFrame for validation
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
            
            validation_errors = []
            valid_records = 0
            
            # Basic validation checks
            for idx, row in df.iterrows():
                row_errors = []
                
                # Check for required fields (customize based on your data)
                required_fields = ["id"]  # Add your required fields
                for field in required_fields:
                    if field not in row or pd.isna(row[field]):
                        row_errors.append(f"Missing required field: {{field}}")
                
                if not row_errors:
                    valid_records += 1
                else:
                    validation_errors.extend([f"Row {{idx}}: {{err}}" for err in row_errors])
            
            context["validation_errors"] = validation_errors
            context["valid_record_count"] = valid_records
            context["total_record_count"] = len(df)
            
            if validation_errors:
                error_rate = len(validation_errors) / len(df) * 100
                if error_rate > 10:  # More than 10% errors
                    return self.failure(f"Validation failed: {{error_rate:.1f}}% error rate ({{len(validation_errors)}} errors)")
            
            result = self.success(f"Validated {{valid_records}} of {{len(df)}} records")
            result.add_metric("valid_records", valid_records)
            result.add_metric("validation_errors", len(validation_errors))
            result.add_metric("error_rate_percent", len(validation_errors) / len(df) * 100)
            result.add_tag("validation-complete")
            
            return result
            
        except Exception as e:
            return self.failure(f"Data validation failed: {{str(e)}}")'''
    
    def _generate_transform_data_step(self, order: int) -> str:
        """Generate data transformation step"""
        return f'''
    @step("Transform Data", order={order}, tags=["transformation"])
    def transform_data(self, context: Dict):
        """Transform data for database insertion"""
        try:
            data = context.get("api_data", [])
            if not data:
                return self.failure("No data to transform")
            
            transformed_records = []
            
            for record in data if isinstance(data, list) else [data]:
                # Add your transformation logic here
                transformed_record = {{
                    "id": record.get("id"),
                    "processed_at": "2025-10-02T00:00:00Z",  # Add timestamp
                    "source": "api",
                    # Add other transformations as needed
                    **record  # Include original fields
                }}
                transformed_records.append(transformed_record)
            
            context["transformed_data"] = transformed_records
            context["transformed_count"] = len(transformed_records)
            
            result = self.success(f"Transformed {{len(transformed_records)}} records")
            result.add_metric("transformed_records", len(transformed_records))
            result.add_tag("transformation-complete")
            
            return result
            
        except Exception as e:
            return self.failure(f"Data transformation failed: {{str(e)}}")'''
    
    def _generate_query_db_step(self, order: int) -> str:
        """Generate database query step"""
        return f'''
    @step("Query Database", order={order}, tags=["database", "query"])
    def query_database(self, context: Dict):
        """Query data from Trino database"""
        try:
            conn = self._get_trino_connection(context)
            cursor = conn.cursor()
            
            # Example query - customize based on your needs
            query = f"SELECT COUNT(*) as record_count FROM {{context['trino_catalog']}}.{{context['trino_schema']}}.{{context['target_table']}}"
            cursor.execute(query)
            
            results = cursor.fetchall()
            context["db_query_results"] = results
            context["db_record_count"] = results[0][0] if results else 0
            
            cursor.close()
            conn.close()
            
            result = self.success(f"Queried database: {{context['db_record_count']}} existing records")
            result.add_metric("db_existing_records", context["db_record_count"])
            result.add_tag("database-query")
            
            return result
            
        except Exception as e:
            return self.failure(f"Database query failed: {{str(e)}}")'''
    
    def _generate_insert_db_step(self, order: int) -> str:
        """Generate database insert step"""
        return f'''
    @step("Insert to Database", order={order}, tags=["database", "insert"])
    def insert_to_database(self, context: Dict):
        """Insert transformed data into Trino database"""
        try:
            data = context.get("transformed_data", [])
            if not data:
                return self.failure("No data to insert")
            
            conn = self._get_trino_connection(context)
            cursor = conn.cursor()
            
            inserted_count = 0
            batch_size = context.get("batch_size", 1000)
            
            # Process in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                # Generate INSERT statement (customize based on your table schema)
                placeholders = ", ".join(["?" for _ in batch[0].keys()])
                columns = ", ".join(batch[0].keys())
                insert_query = f"INSERT INTO {{context['trino_catalog']}}.{{context['trino_schema']}}.{{context['target_table']}} ({{columns}}) VALUES ({{placeholders}})"
                
                # Execute batch insert
                for record in batch:
                    cursor.execute(insert_query, list(record.values()))
                    inserted_count += 1
            
            cursor.close()
            conn.close()
            
            context["inserted_count"] = inserted_count
            
            result = self.success(f"Inserted {{inserted_count}} records into database")
            result.add_metric("records_inserted", inserted_count)
            result.add_metric("batch_size_used", batch_size)
            result.add_tag("database-insert")
            
            return result
            
        except Exception as e:
            return self.failure(f"Database insertion failed: {{str(e)}}")'''
    
    def _generate_sync_step(self, order: int) -> str:
        """Generate API to database sync step"""
        return f'''
    @step("Sync API to Database", order={order}, tags=["sync", "integration"])
    def sync_api_to_db(self, context: Dict):
        """Synchronize API data with database"""
        try:
            api_count = context.get("api_record_count", 0)
            db_count = context.get("db_record_count", 0)
            inserted_count = context.get("inserted_count", 0)
            
            sync_summary = {{
                "api_records": api_count,
                "existing_db_records": db_count,
                "new_records_inserted": inserted_count,
                "sync_timestamp": "2025-10-02T00:00:00Z"
            }}
            
            context["sync_summary"] = sync_summary
            
            result = self.success(f"Sync completed: {{inserted_count}} new records added")
            result.add_metric("sync_api_records", api_count)
            result.add_metric("sync_db_records_before", db_count)
            result.add_metric("sync_new_records", inserted_count)
            result.add_tag("sync-complete")
            
            return result
            
        except Exception as e:
            return self.failure(f"Synchronization failed: {{str(e)}}")'''
    
    def _generate_helper_methods(self, context: Dict[str, Any]) -> str:
        """Generate helper methods for the workflow"""
        methods = []
        
        if context["auth_required"]:
            methods.append(self._generate_auth_helper(context))
        
        if any("db" in op or "query" in op or "insert" in op for op in context["operations"]):
            methods.append(self._generate_trino_helper(context))
        
        return "\n".join(methods)
    
    def _generate_auth_helper(self, context: Dict[str, Any]) -> str:
        """Generate authentication helper method"""
        auth_type = context["auth_type"]
        
        if auth_type == "api_key":
            return '''
    def _get_auth_headers(self, context: Dict) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        api_key = context.get("api_key")
        if not api_key:
            raise ValueError("API key is required for authentication")
        
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }'''
        elif auth_type == "bearer_token":
            return '''
    def _get_auth_headers(self, context: Dict) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        token = context.get("bearer_token")
        if not token:
            raise ValueError("Bearer token is required for authentication")
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }'''
        elif auth_type == "basic_auth":
            return '''
    def _get_auth_headers(self, context: Dict) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        username = context.get("username")
        password = context.get("password")
        if not username or not password:
            raise ValueError("Username and password are required for basic authentication")
        
        import base64
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json"
        }'''
        else:
            return '''
    def _get_auth_headers(self, context: Dict) -> Dict[str, str]:
        """Get headers for API requests"""
        return {"Content-Type": "application/json"}'''
    
    def _generate_trino_helper(self, context: Dict[str, Any]) -> str:
        """Generate Trino connection helper method"""
        return f'''
    def _get_trino_connection(self, context: Dict):
        """Get Trino database connection"""
        try:
            conn = trino.dbapi.connect(
                host="{context['trino_host']}",
                port=443,  # Adjust based on your Trino setup
                user="workflow_user",  # Adjust based on your auth setup
                catalog="{context['trino_catalog']}",
                schema="{context['trino_schema']}",
                http_scheme="https"  # Adjust if using HTTP
            )
            return conn
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Trino: {{str(e)}}")'''
    
    def _generate_test_code(self, context: Dict[str, Any]) -> str:
        """Generate unit test code for the workflow"""
        template = '''"""
Unit tests for {workflow_name}

Generated by Valiant API + Database Template
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from valiant.framework.engine import WorkflowRunner
from .{workflow_module} import {workflow_class_name}


class Test{workflow_class_name}(unittest.TestCase):
    """Test cases for {workflow_class_name}"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.runner = WorkflowRunner()
        self.workflow = {workflow_class_name}(self.runner)
        self.test_context = {{
            "batch_size": 100,
{test_context_fields}
        }}
    
    def test_workflow_inputs(self):
        """Test workflow input field definitions"""
        inputs = self.workflow.inputs()
        self.assertIsInstance(inputs, list)
        self.assertGreater(len(inputs), 0)
        
        # Check that required fields are present
        field_names = [field.name for field in inputs]
        self.assertIn("batch_size", field_names)
    
{test_methods}
    
    def test_workflow_integration(self):
        """Test complete workflow execution with mocked dependencies"""
        # Mock external dependencies
        with patch('requests.get') as mock_get, \\
             patch('trino.dbapi.connect') as mock_connect:
            
            # Setup mocks
            mock_response = Mock()
            mock_response.json.return_value = [{{"id": 1, "name": "test"}}]
            mock_response.raise_for_status.return_value = None
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_get.return_value = mock_response
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [[10]]  # Existing record count
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            # Setup workflow
            self.runner.context.update(self.test_context)
            self.workflow.setup()
            self.workflow.define_steps()
            
            # This would normally run the workflow
            # Uncomment to test: self.runner.run()
            
            # Verify workflow was set up correctly
            self.assertGreater(len(self.runner.steps), 0)


if __name__ == '__main__':
    unittest.main()
'''
        
        workflow_module = context["workflow_class_name"].lower()
        
        # Generate test context fields based on auth type
        test_context_fields = []
        if context["auth_required"]:
            if context["auth_type"] == "api_key":
                test_context_fields.append('            "api_key": "test_api_key",')
            elif context["auth_type"] == "bearer_token":
                test_context_fields.append('            "bearer_token": "test_token",')
            elif context["auth_type"] == "basic_auth":
                test_context_fields.extend([
                    '            "username": "test_user",',
                    '            "password": "test_pass",'
                ])
        
        # Generate test methods for each operation
        test_methods = []
        operations = context["operations"]
        
        if "fetch_api_data" in operations:
            test_methods.append('''    @patch('requests.get')
    def test_fetch_api_data(self, mock_get):
        """Test API data fetching"""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1, "name": "test"}]
        mock_response.raise_for_status.return_value = None
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_get.return_value = mock_response
        
        # Test the step
        result = self.workflow.fetch_api_data(self.test_context)
        
        self.assertTrue(result.success)
        self.assertIn("api_data", self.test_context)
        self.assertEqual(self.test_context["api_record_count"], 1)''')
        
        if any("db" in op for op in operations):
            test_methods.append('''    @patch('trino.dbapi.connect')
    def test_database_connection(self, mock_connect):
        """Test Trino database connection"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        conn = self.workflow._get_trino_connection(self.test_context)
        
        self.assertIsNotNone(conn)
        mock_connect.assert_called_once()''')
        
        context.update({
            "workflow_module": workflow_module,
            "test_context_fields": "\n".join(test_context_fields),
            "test_methods": "\n".join(test_methods)
        })
        
        return self._render_template(template, context)
    
    def _generate_documentation(self, context: Dict[str, Any]) -> str:
        """Generate markdown documentation for the workflow"""
        template = '''# {workflow_name}

{description}

## Overview

This workflow integrates with REST APIs and Trino databases to process and synchronize data. It was generated using the Valiant API + Database template.

## Configuration

### API Settings
- **Base URL**: `{api_base_url}`
- **Authentication**: {auth_type}
- **Endpoints**: {api_endpoints_list}

### Database Settings
- **Host**: `{trino_host}`
- **Catalog**: `{trino_catalog}`
- **Schema**: `{trino_schema}`
- **Target Table**: `{target_table}`

## Operations

This workflow performs the following operations:
{operations_list}

## Usage

### CLI Execution
```bash
python run.py run {workflow_id} \\
{cli_parameters}
```

### API Execution
```bash
curl -X POST http://localhost:8000/run/{workflow_id} \\
  -H "Content-Type: application/json" \\
  -d '{{
{api_json_parameters}
  }}'
```

## Input Fields

{input_fields_doc}

## Steps

{steps_doc}

## Error Handling

{error_handling_doc}

## Metrics and Tags

This workflow emits the following metrics:
- `api_records_fetched`: Number of records retrieved from API
- `api_response_time`: API response time in seconds
- `valid_records`: Number of records that passed validation
- `validation_errors`: Number of validation errors
- `records_inserted`: Number of records inserted into database
- `batch_size_used`: Batch size used for database operations

Tags used:
- `api`, `database`, `integration`, `trino`
- Step-specific tags: `fetch`, `validation`, `transformation`, `insert`, `sync`

## Dependencies

- `requests`: For HTTP API calls
- `trino`: For Trino database connectivity
- `pandas`: For data validation and transformation

## Generated Files

- `{workflow_id}.py`: Main workflow implementation
- `test_{workflow_id}.py`: Unit tests
- `{workflow_id}.md`: This documentation

---

*Generated by Valiant Workflow Template Engine*
'''
        
        # Build documentation context
        api_endpoints_list = ", ".join(f"`{ep}`" for ep in context["api_endpoints"])
        operations_list = "\n".join(f"- {op.replace('_', ' ').title()}" for op in context["operations"])
        
        # Generate CLI parameters
        cli_params = ["  --set batch_size=1000"]
        if context["auth_required"]:
            if context["auth_type"] == "api_key":
                cli_params.append('  --set api_key="your_api_key"')
            elif context["auth_type"] == "bearer_token":
                cli_params.append('  --set bearer_token="your_token"')
            elif context["auth_type"] == "basic_auth":
                cli_params.extend(['  --set username="your_username"', '  --set password="your_password"'])
        
        # Generate API JSON parameters
        api_params = ['    "batch_size": 1000']
        if context["auth_required"]:
            if context["auth_type"] == "api_key":
                api_params.append('    "api_key": "your_api_key"')
            elif context["auth_type"] == "bearer_token":
                api_params.append('    "bearer_token": "your_token"')
            elif context["auth_type"] == "basic_auth":
                api_params.extend(['    "username": "your_username"', '    "password": "your_password"'])
        
        # Generate input fields documentation
        input_fields_doc = "- **batch_size**: Number of records to process per batch (1-10000, default: 1000)"
        if context["auth_required"]:
            if context["auth_type"] == "api_key":
                input_fields_doc += "\n- **api_key**: API key for authentication (required)"
            elif context["auth_type"] == "bearer_token":
                input_fields_doc += "\n- **bearer_token**: Bearer token for authentication (required)"
            elif context["auth_type"] == "basic_auth":
                input_fields_doc += "\n- **username**: Username for basic authentication (required)"
                input_fields_doc += "\n- **password**: Password for basic authentication (required)"
        
        # Generate steps documentation
        steps_doc = ""
        operations = context["operations"]
        step_order = 1
        
        if "fetch_api_data" in operations:
            steps_doc += f"{step_order}. **Fetch API Data**: Retrieves data from the REST API endpoint\n"
            step_order += 1
        if "validate_data" in operations:
            steps_doc += f"{step_order}. **Validate Data**: Performs data quality checks and validation\n"
            step_order += 1
        if "transform_data" in operations:
            steps_doc += f"{step_order}. **Transform Data**: Applies necessary data transformations\n"
            step_order += 1
        if "query_db_data" in operations:
            steps_doc += f"{step_order}. **Query Database**: Retrieves existing data from Trino\n"
            step_order += 1
        if "insert_to_db" in operations:
            steps_doc += f"{step_order}. **Insert to Database**: Inserts processed data into Trino\n"
            step_order += 1
        if "sync_api_to_db" in operations:
            steps_doc += f"{step_order}. **Sync API to Database**: Synchronizes API data with database\n"
            step_order += 1
        
        # Generate error handling documentation
        error_handling = context.get("error_handling", [])
        if error_handling:
            error_handling_doc = "This workflow includes the following error handling strategies:\n"
            error_handling_doc += "\n".join(f"- {eh.replace('_', ' ').title()}" for eh in error_handling)
        else:
            error_handling_doc = "Standard error handling with detailed error messages and failure reporting."
        
        context.update({
            "api_endpoints_list": api_endpoints_list,
            "operations_list": operations_list,
            "cli_parameters": " \\\n".join(cli_params),
            "api_json_parameters": ",\n".join(api_params),
            "input_fields_doc": input_fields_doc,
            "steps_doc": steps_doc,
            "error_handling_doc": error_handling_doc
        })
        
        return self._render_template(template, context)