"""
API to Database Sync Workflow
Demonstrates REST API fetching, schema validation, passing context across steps,
and executing real SQL queries against an SQLite database.
"""
import sqlite3
import requests
import time
from pathlib import Path
from typing import Dict, Any, List

from backend.valiant import Workflow, step, workflow, InputField, InputType


@workflow(
    name="api_db_sync",
    description="Fetch users from REST API, validate response data, load into SQLite table, and verify with SQL query",
    tags=["api", "validation", "database", "sql"]
)
class ApiDbSyncWorkflow(Workflow):
    name = "API to Database Sync"
    description = "REST API extraction, data validation, and SQLite database ingestion"
    version = "3.0.0"
    tags = ["api", "validation", "sql"]

    def inputs(self):
        return [
            InputField(
                name="api_url",
                type=InputType.TEXT,
                default="https://jsonplaceholder.typicode.com/users",
                help_text="Target REST API endpoint URL"
            ),
            InputField(
                name="min_user_id",
                type=InputType.NUMBER,
                default=1,
                min_value=1,
                help_text="Filter out users with ID below this threshold"
            ),
            InputField(
                name="target_table",
                type=InputType.TEXT,
                default="synced_customers",
                help_text="SQLite database table to store records"
            )
        ]

    @step("Fetch API Data", order=1, tags=["api", "http"])
    def fetch_api_data(self, context):
        api_url = context.get("api_url", "https://jsonplaceholder.typicode.com/users")
        start_time = time.time()

        try:
            resp = requests.get(api_url, timeout=10)
            latency = round(time.time() - start_time, 3)

            # 1. HTTP Status Code Validation
            if resp.status_code != 200:
                return self.failure(
                    message=f"API Validation Error: Expected HTTP 200, received HTTP {resp.status_code}",
                    data={
                        "endpoint": api_url,
                        "status_code": resp.status_code,
                        "latency_seconds": latency,
                        "response_body_preview": resp.text[:200]
                    }
                )

            # 2. Content-Type and JSON Payload Parsing Validation
            try:
                raw_users = resp.json()
            except Exception as json_err:
                return self.failure(
                    message=f"JSON Parse Error: API returned invalid JSON payload - {str(json_err)}",
                    error=str(json_err),
                    data={"content_type": resp.headers.get("content-type"), "raw_body": resp.text[:200]}
                )

            # 3. Payload Type Validation (must be a non-empty list)
            if not isinstance(raw_users, list):
                return self.failure(
                    message=f"Schema Validation Error: Expected JSON Array [list], received {type(raw_users).__name__}",
                    data={"received_type": type(raw_users).__name__, "sample": raw_users}
                )

            if len(raw_users) == 0:
                return self.failure(
                    message="Empty Payload Error: API returned an empty list [0 records]",
                    data={"records_count": 0}
                )

        except requests.exceptions.RequestException as req_err:
            return self.failure(
                message=f"Network Connection Failure: Unable to reach {api_url}",
                error=str(req_err),
                data={"url": api_url, "error_type": type(req_err).__name__}
            )

        # Save to context for Step 2
        context["raw_users"] = raw_users

        res = self.success(
            message=f"API Response Validated: Received HTTP 200 with {len(raw_users)} valid records ({latency}s)",
            data={
                "status_code": 200,
                "latency_seconds": latency,
                "total_records": len(raw_users),
                "schema_valid": True,
                "preview": raw_users[:2]
            }
        )
        res.add_metric("api_latency_s", latency)
        res.add_metric("records_fetched", len(raw_users))
        return res

    @step("Validate & Cleanse Records", order=2, requires=["Fetch API Data"], tags=["validation"])
    def validate_and_cleanse(self, context):
        raw_users = context.get("raw_users", [])
        min_id = int(context.get("min_user_id", 1))

        valid_users: List[Dict[str, Any]] = []
        rejected_count = 0

        for u in raw_users:
            user_id = u.get("id", 0)
            email = u.get("email", "")

            # Validation rules: ID >= min_id and email format valid
            if user_id >= min_id and "@" in email:
                company_name = u.get("company", {}).get("name", "Independent") if isinstance(u.get("company"), dict) else "Independent"
                city = u.get("address", {}).get("city", "Unknown") if isinstance(u.get("address"), dict) else "Unknown"

                valid_users.append({
                    "id": user_id,
                    "name": u.get("name", "").strip(),
                    "email": email.strip().lower(),
                    "company": company_name,
                    "city": city
                })
            else:
                rejected_count += 1

        # Fail if all records fail validation
        if len(valid_users) == 0:
            return self.failure(
                message=f"Validation Threshold Error: 0 out of {len(raw_users)} records passed schema criteria (min_user_id={min_id})",
                data={
                    "total_input_records": len(raw_users),
                    "min_user_id_threshold": min_id,
                    "rejected_count": rejected_count,
                    "pass_rate": 0.0
                }
            )

        # Pass cleansed records to Step 3
        context["clean_users"] = valid_users

        pass_rate = round(len(valid_users) / max(len(raw_users), 1), 2)
        res = self.success(
            message=f"Validated {len(valid_users)} records ({rejected_count} filtered out, pass rate {int(pass_rate*100)}%)",
            data={
                "validated_count": len(valid_users),
                "rejected_count": rejected_count,
                "pass_rate": pass_rate,
                "sample_transformed": valid_users[:2]
            }
        )
        res.add_metric("validation_pass_rate", pass_rate)
        res.add_metric("valid_users_count", len(valid_users))
        return res

    @step("Load Into SQLite Database", order=3, requires=["Validate & Cleanse Records"], tags=["database", "sql"])
    def load_to_database(self, context):
        users = context.get("clean_users", [])
        table_name = context.get("target_table", "synced_customers")
        db_path = Path.cwd() / "valiant.db"

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # DDL: Create table if not exists
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT,
                city TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # DML: Insert or replace rows
        for u in users:
            cursor.execute(f"""
                INSERT OR REPLACE INTO {table_name} (id, name, email, company, city)
                VALUES (?, ?, ?, ?, ?)
            """, (u["id"], u["name"], u["email"], u["company"], u["city"]))

        conn.commit()
        conn.close()

        res = self.success(
            message=f"Executed INSERT OR REPLACE for {len(users)} rows into table '{table_name}'",
            data={
                "database": "valiant.db",
                "table": table_name,
                "rows_affected": len(users),
                "sql_schema": f"{table_name}(id, name, email, company, city)"
            }
        )
        res.add_metric("rows_written", len(users))
        return res

    @step("Verify Data via SQL Query", order=4, requires=["Load Into SQLite Database"], tags=["database", "sql", "verification"])
    def verify_query(self, context):
        table_name = context.get("target_table", "synced_customers")
        db_path = Path.cwd() / "valiant.db"

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Query data back from SQLite
        cursor.execute(f"SELECT id, name, email, company, city FROM {table_name} ORDER BY id ASC LIMIT 5")
        rows = cursor.fetchall()
        conn.close()

        queried_results = [
            {"id": r[0], "name": r[1], "email": r[2], "company": r[3], "city": r[4]}
            for r in rows
        ]

        res = self.success(
            message=f"Queried {len(queried_results)} sample rows from '{table_name}'",
            data={
                "query": f"SELECT id, name, email, company, city FROM {table_name} LIMIT 5",
                "total_rows_queried": len(queried_results),
                "rows": queried_results
            }
        )
        res.add_metric("queried_rows_count", len(queried_results))
        return res
