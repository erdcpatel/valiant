"""Dashboard page — overview stats and recent runs."""
from __future__ import annotations

dashboard_md = """
<|layout|columns=1 1 1|gap=20px|
<|part|class_name=card|
### Total Runs
<|{total_runs}|text|class_name=stat-number|>
|>
<|part|class_name=card|
### Success Rate
<|{success_rate}|text|class_name=stat-number stat-success|>
|>
<|part|class_name=card|
### Failed Runs
<|{failed_runs}|text|class_name=stat-number stat-error|>
|>
|>

---

## Recent Runs

<|{history_rows}|table|columns=workflow_name status triggered_by started_at duration_ms|width=100%|page_size=10|>
"""
