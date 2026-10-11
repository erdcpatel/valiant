"""
Demo Workflow - Showcases parallel steps, dependencies, metrics, and conditional execution.
"""
from typing import Dict
import time
from backend.valiant import Workflow, step, workflow, InputField, InputType


@workflow(
    name="demo",
    description="Demonstrates multi-step workflow with parallel tasks, metrics, and conditional notifications",
    tags=["demo", "sample", "core"]
)
class DemoWorkflow(Workflow):
    name = "Demo Pipeline"
    description = "Showcase of parallel execution, step metrics, and conditional notifications"
    version = "3.0.0"
    author = "Valiant Team"
    tags = ["demo", "parallel", "metrics"]

    profiles = {
        "dev": {
            "user_name": "Dev Sandbox Runner",
            "processing_mode": "fast",
            "max_items": 20,
            "notify_on_complete": False,
        },
        "uat": {
            "user_name": "QA Lead (UAT Testing)",
            "processing_mode": "standard",
            "max_items": 150,
            "notify_on_complete": True,
        },
        "prod": {
            "user_name": "Platform Ops (Production Run)",
            "processing_mode": "thorough",
            "max_items": 500,
            "notify_on_complete": True,
        },
    }

    def inputs(self):
        return [
            InputField(
                name="user_name",
                type=InputType.TEXT,
                required=True,
                default="Alice",
                help_text="Name of the user running this demo"
            ),
            InputField(
                name="processing_mode",
                type=InputType.SELECT,
                options=["fast", "standard", "thorough"],
                default="standard",
                help_text="Level of computation depth"
            ),
            InputField(
                name="max_items",
                type=InputType.NUMBER,
                default=50,
                min_value=5,
                max_value=1000,
                help_text="Maximum records to process"
            ),
            InputField(
                name="notify_on_complete",
                type=InputType.CHECKBOX,
                default=True,
                help_text="Send completion notification"
            )
        ]

    @step("Validate Inputs", order=1, tags=["validation"])
    def validate_inputs(self, context):
        user_name = context.get("user_name", "").strip()
        if not user_name:
            return self.failure("User name must not be empty")

        mode = context.get("processing_mode", "standard")
        items = int(context.get("max_items", 50))

        context["session_id"] = f"sess_{int(time.time())}"
        context["target_items"] = items

        res = self.success(f"Validated configuration for user '{user_name}' ({mode} mode)")
        res.add_metric("target_items", items)
        res.add_metric("mode", mode)
        return res

    # --- TIER 2: 4 PARALLEL DATA INGESTION STEPS ---
    @step(
        "Fetch Account Data",
        order=2,
        parallel_group="data_fetch",
        requires=["Validate Inputs"],
        tags=["io", "fetch"]
    )
    def fetch_account_data(self, context):
        time.sleep(0.3)
        context["accounts"] = ["acc_101", "acc_102", "acc_103"]
        res = self.success("Fetched 3 active accounts")
        res.add_metric("accounts_fetched", 3)
        return res

    @step(
        "Fetch Transaction Data",
        order=2,
        parallel_group="data_fetch",
        requires=["Validate Inputs"],
        tags=["io", "fetch"]
    )
    def fetch_transaction_data(self, context):
        time.sleep(0.4)
        items = context.get("target_items", 50)
        context["transactions"] = [f"tx_{i}" for i in range(items)]
        res = self.success(f"Fetched {items} transactions")
        res.add_metric("transactions_fetched", items)
        return res

    @step(
        "Fetch Risk & Credit Scoring",
        order=2,
        parallel_group="data_fetch",
        requires=["Validate Inputs"],
        tags=["ml", "risk", "fetch"]
    )
    def fetch_risk_scoring(self, context):
        time.sleep(0.35)
        context["risk_score"] = 782
        context["risk_rating"] = "LOW_RISK"
        res = self.success("Risk model computed credit score: 782 (Tier: LOW_RISK)")
        res.add_metric("credit_score", 782)
        return res

    @step(
        "Fetch Compliance & KYC Records",
        order=2,
        parallel_group="data_fetch",
        requires=["Validate Inputs"],
        tags=["compliance", "kyc", "fetch"]
    )
    def fetch_kyc_records(self, context):
        time.sleep(0.25)
        context["kyc_verified"] = True
        res = self.success("KYC check verified: AML clear, PEP clear")
        res.add_metric("aml_violations", 0)
        return res

    # --- TIER 3: CONSOLIDATION & TRANSFORMATION (1 SEQUENTIAL STEP) ---
    @step(
        "Aggregate & Transform",
        order=3,
        requires=[
            "Fetch Account Data",
            "Fetch Transaction Data",
            "Fetch Risk & Credit Scoring",
            "Fetch Compliance & KYC Records"
        ],
        tags=["aggregation"]
    )
    def aggregate_data(self, context):
        time.sleep(0.2)
        accounts = context.get("accounts", [])
        transactions = context.get("transactions", [])
        risk_score = context.get("risk_score", 0)
        kyc_verified = context.get("kyc_verified", False)

        summary = {
            "account_count": len(accounts),
            "tx_count": len(transactions),
            "risk_score": risk_score,
            "kyc_verified": kyc_verified,
            "avg_tx_per_account": round(len(transactions) / max(len(accounts), 1), 1)
        }
        context["summary"] = summary

        res = self.success(f"Aggregated {len(transactions)} txs across {len(accounts)} accounts. Risk score: {risk_score}.")
        res.add_metric("avg_tx_per_account", summary["avg_tx_per_account"])
        return res

    # --- TIER 4: 2 PARALLEL NOTIFICATION DISPATCHES ---
    @step(
        "Send Email Notification",
        order=4,
        parallel_group="notifications",
        condition="notify_on_complete",
        requires=["Aggregate & Transform"],
        tags=["notification", "email"]
    )
    def send_email_notification(self, context):
        user_name = context.get("user_name")
        summary = context.get("summary", {})
        time.sleep(0.2)
        res = self.success(f"Audit email dispatched to {user_name} (Status: Delivered)")
        res.add_metric("email_delivered", True)
        return res

    @step(
        "Publish Webhook Event",
        order=4,
        parallel_group="notifications",
        condition="notify_on_complete",
        requires=["Aggregate & Transform"],
        tags=["notification", "webhook"]
    )
    def publish_webhook_event(self, context):
        time.sleep(0.2)
        session_id = context.get("session_id")
        res = self.success(f"Webhook broadcasted event 'audit.completed' for session {session_id}")
        res.add_metric("webhook_status", 200)
        return res

    # --- TIER 5: FINAL AUDIT SIGN-OFF (1 SEQUENTIAL STEP) ---
    @step(
        "Generate Final Audit Log",
        order=5,
        requires=["Send Email Notification", "Publish Webhook Event"],
        tags=["audit", "compliance"]
    )
    def generate_audit_log(self, context):
        time.sleep(0.15)
        session_id = context.get("session_id")
        res = self.success(f"Session {session_id} archived to persistent audit ledger with cryptographic signature")
        res.add_metric("audit_hash_verified", True)
        return res
