"""History page — filterable execution history powered by Polars."""
from __future__ import annotations

history_md = """
## Execution History

<|layout|columns=1 1 1 1|gap=15px|
<|{history_workflow_options}|selector|value={history_filter_workflow}|on_change=on_history_filter_change|label=Workflow|dropdown|width=100%|>
<|{history_status_options}|selector|value={history_filter_status}|on_change=on_history_filter_change|label=Status|dropdown|width=100%|>
<|{history_limit}|number|label=Limit|on_change=on_history_filter_change|>
<|Refresh|button|on_action=on_history_refresh|>
|>

---

<|{history_rows}|table|columns=workflow_name status triggered_by started_at duration_ms|width=100%|page_size=20|>
"""
