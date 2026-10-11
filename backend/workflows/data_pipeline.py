"""
Data Pipeline Workflow - Simulates an ETL ingestion process with batching, validation, and metrics.
"""
import time
from backend.valiant import Workflow, step, workflow, InputField, InputType


@workflow(
    name="data_pipeline",
    description="Extracts records, performs schema validation, and batches into analytics storage",
    tags=["etl", "data", "analytics"]
)
class DataPipelineWorkflow(Workflow):
    name = "ETL Ingestion Pipeline"
    description = "Ingest, validate, and load time-series records"
    version = "3.0.0"
    tags = ["data", "etl", "analytics"]

    def inputs(self):
        return [
            InputField("dataset_name", type=InputType.TEXT, default="events_stream", required=True),
            InputField("batch_size", type=InputType.NUMBER, default=500, min_value=10, max_value=5000),
            InputField("target_table", type=InputType.TEXT, default="analytics.fact_events", required=True),
            InputField("dry_run", type=InputType.CHECKBOX, default=False)
        ]

    @step("Extract Source Records", order=1, tags=["extract", "io"])
    def extract_records(self, context):
        dataset = context.get("dataset_name")
        batch_size = int(context.get("batch_size", 500))
        time.sleep(0.3)

        records = [{"id": i, "val": i * 1.5} for i in range(batch_size)]
        context["extracted_records"] = records

        res = self.success(f"Extracted {len(records)} records from source '{dataset}'")
        res.add_metric("records_extracted", len(records))
        res.add_metric("extraction_rate_rec_per_sec", round(len(records) / 0.3, 1))
        return res

    @step("Validate Schema & Cleanse", order=2, requires=["Extract Source Records"], tags=["transform"])
    def validate_schema(self, context):
        records = context.get("extracted_records", [])
        time.sleep(0.2)
        valid_records = [r for r in records if r["val"] >= 0]
        context["cleaned_records"] = valid_records

        res = self.success(f"Validated {len(valid_records)} records (0 rejected)")
        res.add_metric("valid_ratio", 1.0)
        res.add_metric("records_passed", len(valid_records))
        return res

    @step("Load to Target", order=3, requires=["Validate Schema & Cleanse"], tags=["load", "database"])
    def load_to_target(self, context):
        target = context.get("target_table")
        records = context.get("cleaned_records", [])
        dry_run = context.get("dry_run", False)
        time.sleep(0.3)

        if dry_run:
            msg = f"[DRY RUN] Would load {len(records)} records to {target}"
        else:
            msg = f"Successfully loaded {len(records)} records into {target}"

        res = self.success(msg)
        res.add_metric("records_loaded", len(records) if not dry_run else 0)
        res.add_metric("target_table", target)
        return res
