# Quick Start: Valiant Template System

## 🚀 Create Your First Workflow in 5 Minutes

The Valiant Template System eliminates the "blank page problem" by generating complete, production-ready workflows from simple questions.

### Step 1: Run Template Command

```bash
python run.py create
```

This shows available templates in a rich table format.

### Step 2: Select Template

```bash
python run.py create api_db_integration
```

### Step 3: Answer Configuration Questions

The system will guide you through questions like:

```
✨ What should we call this workflow? User Data Sync
✨ Brief description? Synchronize user data from API to database
✨ What's the base URL of the API? https://api.company.com
✨ Which API endpoints will you use? GET /users, POST /users
✨ What authentication does the API use? api_key
✨ Trino database host? trino.company.com:443
✨ Target table name? user_sync_table
✨ What operations should this workflow perform? fetch_api_data, validate_data, insert_to_db
```

### Step 4: Get Complete Workflow Package

**Generated Files:**
- `user_data_sync.py` - Complete workflow implementation
- `test_user_data_sync.py` - Unit test suite with mocking
- `user_data_sync.md` - Comprehensive documentation

### Step 5: Run Your Generated Workflow

```bash
python run.py run user_data_sync --set api_key="your_key" --set batch_size=500
```

## 🎯 What You Get

### Complete Workflow Code
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
    
    @step("Validate Data", order=2, tags=["validation"])
    def validate_data(self, context: Dict):
        # Pandas-based validation logic
    
    @step("Insert to Database", order=3, tags=["database"])
    def insert_to_database(self, context: Dict):
        # Trino batch insert with connection management
```

### Unit Tests with Mocking
```python
class TestUserDataSyncWorkflow(unittest.TestCase):
    @patch('requests.get')
    def test_fetch_api_data(self, mock_get):
        # Complete test implementation
```

### Documentation with Examples
- Usage instructions with CLI and API examples
- Input field documentation
- Step-by-step workflow explanation
- Error handling strategies
- Metrics and monitoring information

## ⚡ Productivity Impact

**Before (Manual):**
```
Research patterns:     30-60 minutes
Write workflow:        60-90 minutes  
Add error handling:    30-45 minutes
Write tests:           45-60 minutes
Create docs:           20-30 minutes
─────────────────────
Total: 3.5-5 hours
```

**After (Templates):**
```
Run template:          1 minute
Answer questions:      5-10 minutes
Review/customize:      15-30 minutes
─────────────────────
Total: 20-40 minutes
```

**Result: 85-90% time reduction** 🚀

## 🔧 Template Options

### API + Database Integration
Perfect for workflows that:
- Connect to REST APIs with authentication
- Process and validate data
- Store results in Trino databases
- Need enterprise-grade error handling

**Features Generated:**
- Multiple auth types (API key, Bearer token, Basic auth)
- Data validation with pandas
- Batch database operations
- Retry logic and error handling
- Comprehensive monitoring

### Custom Output Directory
```bash
python run.py create api_db_integration --output ./my_workflows/
```

### Non-Interactive Mode
```bash
python run.py create api_db_integration --non-interactive
```
Uses template defaults for all questions.

## 📚 Next Steps

- **Try it now**: `python run.py create`
- **Read full docs**: [TEMPLATE_SYSTEM_README.md](TEMPLATE_SYSTEM_README.md)
- **Advanced guide**: [WORKFLOW_DEVELOPMENT_GUIDE.md](WORKFLOW_DEVELOPMENT_GUIDE.md)
- **Framework docs**: [README.md](README.md)

---

**Transform your workflow development from hours to minutes!** ⚡