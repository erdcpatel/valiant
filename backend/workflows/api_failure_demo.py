"""
API Failure and Resilience Testing Workflow
Demonstrates various real-world failure patterns and how Valiant:
- Validates API responses (status code, payload format, latency SLAs)
- Displays step errors, HTTP response previews, and diagnostic stack traces
- Handles downstream dependencies (skips dependent steps when an upstream step fails)
- Visualizes failures, retries, and error payloads in the UI
"""
import time
import requests
from typing import List
from backend.valiant import Workflow, step, workflow, InputField, InputType


@workflow(
    name="api_validation_failure_suite",
    description="Simulate and test real API failures (404, 500, Schema mismatch, Latency SLA breach, Auth 401)",
    tags=["testing", "validation", "failures", "api"]
)
class ApiValidationFailureWorkflow(Workflow):
    name = "API Validation & Failure Suite"
    description = "Simulate various failure modes to inspect UI error states, payloads, and dependent skips"
    version = "1.0.0"
    tags = ["testing", "validation", "failures", "api"]

    profiles = {
        "dev": {
            "failure_scenario": "http_404_not_found",
            "mock_endpoint": "https://api.dev.valiant.internal/v1/orders/ORD-99999",
            "timeout_seconds": 10,
        },
        "uat": {
            "failure_scenario": "latency_sla_breach",
            "mock_endpoint": "https://api.uat.valiant.internal/v1/checkout/latency-test",
            "timeout_seconds": 15,
        },
        "prod": {
            "failure_scenario": "none_success",
            "mock_endpoint": "https://api.valiant.internal/v1/health/synthetic-probe",
            "timeout_seconds": 30,
        },
    }

    def inputs(self) -> List[InputField]:
        return [
            InputField(
                name="failure_scenario",
                type=InputType.SELECT,
                default="http_404_not_found",
                options=[
                    "none_success",
                    "http_404_not_found",
                    "http_500_server_error",
                    "invalid_schema_structure",
                    "latency_sla_exceeded",
                    "unauthorized_401"
                ],
                help_text="Choose which real-world failure mode to simulate"
            ),
            InputField(
                name="expected_sla_ms",
                type=InputType.NUMBER,
                default=50,
                min_value=1,
                help_text="Max acceptable response time threshold (ms)"
            )
        ]

    # --- STEP 1: API INGESTION WITH TARGETED FAILURE ---
    @step("Execute Endpoint Probe", order=1, tags=["api", "probe"])
    def step_01_probe(self, context):
        scenario = context.get("failure_scenario", "http_404_not_found")
        sla_threshold = context.get("expected_sla_ms", 50)

        # 1. HTTP 404 Scenario
        if scenario == "http_404_not_found":
            return self.failure(
                message="HTTP 404 Not Found: Requested resource does not exist on target API",
                data={
                    "url": "https://api.internal/v2/missing-resource",
                    "status_code": 404,
                    "reason": "Not Found",
                    "response_body": {
                        "error": "ResourceNotFound",
                        "code": 404,
                        "message": "Resource with identifier 'res_99812' not found"
                    }
                }
            )

        # 2. HTTP 500 Scenario
        elif scenario == "http_500_server_error":
            return self.failure(
                message="HTTP 500 Internal Server Error: Remote service database connection pool exhausted",
                data={
                    "url": "https://api.internal/v1/checkout",
                    "status_code": 500,
                    "reason": "Internal Server Error",
                    "upstream_headers": {"X-Trace-ID": "trace_9981-failed-404"},
                    "error_body": {
                        "fault": "PG::ConnectionBad",
                        "detail": "FATAL: remaining connection slots are reserved for non-replication superuser connections"
                    }
                }
            )

        # 3. Schema Structure Mismatch
        elif scenario == "invalid_schema_structure":
            actual_payload = {"error_code": "MALFORMED_JSON", "data": "unexpected string instead of object"}
            return self.failure(
                message="Schema Validation Failed: Response payload violates contract specification",
                data={
                    "status_code": 200,
                    "validation_errors": [
                        "Field 'items' is missing from root object",
                        "Field 'total_count' expected integer, received null",
                        "Unexpected type: received string where JSON Array was expected"
                    ],
                    "raw_payload_preview": actual_payload
                }
            )

        # 4. Latency SLA Exceeded
        elif scenario == "latency_sla_exceeded":
            actual_latency_ms = 420.5
            res = self.failure(
                message=f"SLA Breach: Endpoint latency {actual_latency_ms}ms exceeds threshold SLA {sla_threshold}ms",
                data={
                    "target_sla_ms": sla_threshold,
                    "actual_latency_ms": actual_latency_ms,
                    "p99_historical_ms": 120.0,
                    "recommendation": "Check upstream network routing or DB query locks"
                }
            )
            res.add_metric("latency_ms", actual_latency_ms)
            return res

        # 5. Unauthorized 401
        elif scenario == "unauthorized_401":
            return self.failure(
                message="HTTP 401 Unauthorized: API token has expired or is invalid",
                data={
                    "status_code": 401,
                    "auth_realm": "Bearer",
                    "error_description": "The access token provided has expired at 2026-10-11T12:00:00Z"
                }
            )

        return self.success("Endpoint responded successfully")

    # --- STEP 2: DEPENDENT STEP (SHOULD BE AUTOMATICALLY SKIPPED ON STEP 1 FAILURE) ---
    @step("Transform & Parse Validated Records", order=2, requires=["Execute Endpoint Probe"], tags=["transform"])
    def step_02_transform(self, context):
        # This will be marked as SKIPPED by Valiant runner when Step 1 fails
        return self.success("Transformed records successfully")

    # --- STEP 3: PERSISTENCE (ALSO SKIPPED) ---
    @step("Commit Records to Database", order=3, requires=["Transform & Parse Validated Records"], tags=["database"])
    def step_03_persist(self, context):
        return self.success("Committed to database")
