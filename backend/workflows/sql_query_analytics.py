"""
SQL Query & Polars Tabular Analytics Workflow.
Demonstrates enterprise-grade SQL query execution, Polars transformations,
regional revenue aggregation, and outlier detection with first-class tabular data support.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random

from backend.valiant import (
    Workflow,
    step,
    workflow,
    InputField,
    InputType,
    WorkflowContext,
)
import polars as pl


@workflow(
    name="sql_query_analytics",
    description="Execute SQL queries, compute Polars aggregations, detect transaction outliers, and export reports",
    tags=["sql", "polars", "analytics", "tabular", "finance"]
)
class SqlQueryAnalyticsWorkflow(Workflow):
    name = "SQL Query & Polars Tabular Analytics"
    description = "Execute SQL queries, compute Polars aggregations, detect transaction outliers, and export reports"
    version = "1.0.0"
    tags = ["sql", "polars", "analytics", "tabular", "finance"]

    def inputs(self) -> List[InputField]:
        return [
            InputField(
                name="row_count",
                type=InputType.NUMBER,
                label="Sample Rows to Query",
                default=500,
                help_text="Number of simulated SQL transactional rows to fetch (100–2,000)"
            ),
            InputField(
                name="min_order_amount",
                type=InputType.NUMBER,
                label="Minimum Order Amount ($)",
                default=25.0,
                help_text="Filter transactions above this threshold"
            ),
            InputField(
                name="outlier_threshold",
                type=InputType.NUMBER,
                label="Outlier Spend Threshold ($)",
                default=750.0,
                help_text="Threshold to flag high-value outlier transactions"
            ),
            InputField(
                name="target_database",
                type=InputType.SELECT,
                label="Target Database Warehouse",
                default="snowflake_prod_db",
                options=["snowflake_prod_db", "postgres_read_replica", "clickhouse_analytics", "duckdb_inmemory"]
            )
        ]

    @step("Fetch SQL Sales Data", order=1, tags=["sql", "query"])
    def fetch_sql_sales_data(self, context) -> Any:
        """
        Execute SQL query against operational warehouse and load results into a native Polars DataFrame.
        """
        row_count = int(context.get("row_count") or 500)
        min_amount = float(context.get("min_order_amount") or 25.0)

        random.seed(42)  # Deterministic seed for reproducible testing
        countries = ["United States", "Germany", "United Kingdom", "Japan", "Canada", "Australia", "France", "Singapore"]
        categories = ["Cloud Infrastructure", "Enterprise SaaS", "Hardware Security", "Professional Services", "AI Compute"]
        statuses = ["completed", "completed", "completed", "completed", "pending", "refunded"]
        names = ["Acme Corp", "Globex Global", "Initech LLC", "Umbrella Group", "Stark Industries", "Wayne Enterprises", "Cyberdyne", "Hooli Inc"]

        base_time = datetime.now() - timedelta(days=30)

        data = {
            "order_id": [f"ORD-{10000 + i}" for i in range(row_count)],
            "customer_id": [1000 + (i % 80) for i in range(row_count)],
            "customer_name": [names[i % len(names)] for i in range(row_count)],
            "country": [countries[i % len(countries)] for i in range(row_count)],
            "category": [categories[i % len(categories)] for i in range(row_count)],
            "order_amount": [round(min_amount + random.random() * 950.0, 2) for i in range(row_count)],
            "discount_rate": [round(random.choice([0.0, 0.05, 0.10, 0.15, 0.20]), 2) for _ in range(row_count)],
            "status": [random.choice(statuses) for _ in range(row_count)],
            "created_at": [(base_time + timedelta(hours=i * 1.5)).strftime("%Y-%m-%d %H:%M:%S") for i in range(row_count)]
        }

        # Build native Polars DataFrame
        df = pl.DataFrame(data).with_columns([
            pl.col("order_amount").cast(pl.Float64),
            pl.col("discount_rate").cast(pl.Float64),
            pl.col("customer_id").cast(pl.Int64),
            pl.col("created_at").str.to_datetime("%Y-%m-%d %H:%M:%S")
        ])

        context["raw_sales_data"] = df
        return self.success(f"Successfully queried {df.height} rows × {df.width} cols from {context.get('target_database')}", data=df)

    @step("Aggregate Regional Revenue", order=2, requires=["Fetch SQL Sales Data"], tags=["polars", "sql", "aggregation"])
    def aggregate_regional_revenue(self, context) -> Any:
        """
        Execute Polars in-memory SQL query to aggregate regional gross revenue, discounts, and order counts.
        """
        raw_df: pl.DataFrame = context["raw_sales_data"]

        # Use Polars SQLContext for in-memory ANSI SQL execution
        sql = pl.SQLContext()
        sql.register("sales", raw_df)

        query = """
            SELECT
                country,
                category,
                count(*) AS total_orders,
                round(sum(order_amount), 2) AS gross_revenue,
                round(avg(order_amount), 2) AS avg_order_value,
                round(sum(order_amount * discount_rate), 2) AS total_discount
            FROM sales
            WHERE status = 'completed'
            GROUP BY country, category
            ORDER BY gross_revenue DESC
        """
        agg_df = sql.execute(query).collect()

        context["regional_summary"] = agg_df
        return self.success(f"Computed regional revenue summary: {agg_df.height} aggregate groups", data=agg_df)

    @step("Detect Outlier Transactions", order=3, requires=["Fetch SQL Sales Data"], tags=["polars", "fraud", "audit"])
    def detect_outlier_transactions(self, context) -> Any:
        """
        Apply Polars vectorized filter expressions to detect high-value anomalous transactions.
        """
        raw_df: pl.DataFrame = context["raw_sales_data"]
        threshold = float(context.get("outlier_threshold") or 750.0)

        # Polars vectorized expression filtering
        outlier_df = raw_df.filter(
            (pl.col("order_amount") >= threshold) |
            ((pl.col("discount_rate") >= 0.15) & (pl.col("order_amount") >= 500.0))
        ).sort("order_amount", descending=True)

        context["outlier_records"] = outlier_df
        return self.success(f"Flagged {outlier_df.height} high-value outlier transactions (>= ${threshold:,.2f})", data=outlier_df)

    @step("Generate Executive Audit", order=4, requires=["Aggregate Regional Revenue", "Detect Outlier Transactions"], tags=["summary"])
    def generate_executive_audit(self, context) -> Any:
        """
        Synthesize audit metrics from Polars DataFrames and log final reconciliation.
        """
        summary_df: pl.DataFrame = context["regional_summary"]
        outlier_df: pl.DataFrame = context["outlier_records"]

        total_gross = summary_df.select(pl.col("gross_revenue").sum()).item()
        total_discount = summary_df.select(pl.col("total_discount").sum()).item()
        net_revenue = round(total_gross - total_discount, 2)

        return self.success(
            f"Audit reconciled: Net Revenue ${net_revenue:,.2f} across {summary_df.height} regions. "
            f"Found {outlier_df.height} transactions needing compliance review."
        )
