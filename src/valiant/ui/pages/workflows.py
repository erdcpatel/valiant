"""Workflows page — select, configure, and run a workflow with live step results."""
from __future__ import annotations

workflows_md = """
<|layout|columns=1 3|gap=30px|

<|part|
## Workflows

<|{workflow_names}|selector|value={selected_workflow}|on_change=on_workflow_selected|dropdown|label=Select a workflow|width=100%|>

<|part|render={selected_workflow != ""}|
---
**<|{selected_workflow}|text|raw|>**

<|{workflow_description}|text|raw|>

Tags: <|{workflow_tags}|text|raw|>
Version: <|{workflow_version}|text|raw|>
|>
|>

<|part|
<|part|render={selected_workflow != ""}|

## Configure Inputs

<|{form_error}|text|class_name=error-message|render={form_error != ""}|>

<|{input_fields}|table|show_all|columns=label type required|width=100%|render={input_fields|len > 0}|>

<|part|render={input_fields|len == 0}|
*This workflow requires no inputs.*
|>

<br/>

**Input Values**

<|{form_values}|>

<br/>

<|Run Workflow|button|on_action=on_run_workflow|active={not is_running}|class_name=primary|>
<|{run_status_label}|text|raw|render={run_status != ""}|>

|>

<|part|render={step_results|len > 0}|

---

## Execution Results  <|{run_id}|text|class_name=run-id|>

<|{step_results}|table|columns=name status message duration_ms attempts|width=100%|show_all|>

<|{run_error}|text|class_name=error-message|render={run_error != ""}|>

|>

|>
|>
"""
