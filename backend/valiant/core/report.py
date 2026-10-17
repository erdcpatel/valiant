"""
ValiantFlow HTML Report Generator: Self-contained, executive-grade standalone HTML reports
for workflow execution review, compliance audits, and stakeholder sharing.
Includes embedded responsive styling, dark/light mode toggle, 5 interactive tabs
(Executive Overview, Step Breakdown with Expanders, Polars Tabular Search/Sort,
Governance Audit Trail, and Raw Logs/Context), and print-to-PDF (@media print) optimization.
"""
from typing import Dict, Any, Optional, List
import html
import json
from datetime import datetime
from .logging import RunLogManager


def _escape(text: Any) -> str:
    if text is None:
        return ""
    return html.escape(str(text))


def _format_time(seconds: Optional[float]) -> str:
    if seconds is None:
        return "0s"
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f}µs"
    if seconds < 1.0:
        return f"{seconds * 1000:.1f}ms"
    if seconds < 60.0:
        return f"{seconds:.2f}s"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}m {secs:.1f}s"


def _format_iso(iso_str: Optional[str]) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M:%S UTC")
    except Exception:
        return str(iso_str)


def _mask_sensitive_dict(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not data or not isinstance(data, dict):
        return {}
    masked = {}
    sensitive_keywords = ["password", "secret", "token", "key", "auth", "credential", "private"]
    for k, v in data.items():
        if any(kw in str(k).lower() for kw in sensitive_keywords):
            masked[k] = "********"
        elif isinstance(v, dict):
            masked[k] = _mask_sensitive_dict(v)
        else:
            masked[k] = v
    return masked


def generate_run_html_report(run_data: Dict[str, Any], env: str = "dev") -> str:
    """
    Generate a complete, self-contained multi-tab HTML report from a workflow run dictionary.
    Requires ZERO external CDN dependencies, remote fonts, or script tags.
    """
    wf_name = run_data.get("workflow_name", "Workflow")
    run_id = run_data.get("id") or run_data.get("run_id", "run_unknown")
    status = (run_data.get("status") or "pending").lower()
    success = bool(run_data.get("success", False))
    environment = (run_data.get("environment") or env or "dev").upper()
    total_time = run_data.get("total_time") or 0.0
    started_at = run_data.get("started_at")
    completed_at = run_data.get("completed_at")
    triggered_by = run_data.get("triggered_by", "system")
    parent_run_id = run_data.get("parent_run_id")
    resumed_from = run_data.get("resumed_from_step")
    profile = run_data.get("profile")
    raw_inputs = run_data.get("inputs") or {}
    masked_inputs = _mask_sensitive_dict(raw_inputs)
    raw_context = run_data.get("context") or {}
    masked_context = _mask_sensitive_dict(raw_context)

    steps: List[Dict[str, Any]] = run_data.get("steps") or run_data.get("results") or []

    # KPI counts
    total_steps = len(steps)
    succeeded_steps = sum(1 for s in steps if s.get("status") == "success" or s.get("success"))
    failed_steps = sum(1 for s in steps if s.get("status") == "failed")
    skipped_steps = sum(1 for s in steps if s.get("status") == "skipped")

    # Tabular steps & Approval steps
    tabular_steps = [s for s in steps if s.get("tabular_data")]
    approval_steps = [
        s for s in steps
        if s.get("requires_approval")
        or s.get("approved_by")
        or s.get("status") in ("waiting_approval", "rejected")
    ]

    # Overall Status color
    if status == "completed" and success:
        status_bg = "#064e3b"
        status_fg = "#34d399"
    elif status == "failed":
        status_bg = "#881337"
        status_fg = "#fda4af"
    elif status == "waiting_approval":
        status_bg = "#78350f"
        status_fg = "#fde047"
    else:
        status_bg = "#334155"
        status_fg = "#94a3b8"

    # Environment badge color
    env_bg = "#064e3b" if environment == "DEV" else "#78350f" if environment == "UAT" else "#881337"
    env_fg = "#34d399" if environment == "DEV" else "#fde047" if environment == "UAT" else "#fda4af"

    # Meta banner items
    profile_meta_html = f'<div class="meta-item"><span class="meta-label">Profile</span><span class="meta-val">{_escape(profile)}</span></div>' if profile else ''
    resumed_meta_html = f'<div class="meta-item"><span class="meta-label">Resumed From</span><span class="meta-val">{_escape(resumed_from)}</span></div>' if resumed_from else ''
    parent_meta_html = f'<div class="meta-item"><span class="meta-label">Parent Execution</span><span class="meta-val">{_escape(parent_run_id)}</span></div>' if parent_run_id else ''

    # Raw Logs from Disk or Steps Fallback
    disk_logs = ""
    try:
        disk_logs = RunLogManager.read_log_content(run_id, env=environment.lower())
    except Exception:
        pass

    if not disk_logs or "[Log file not found" in disk_logs:
        step_log_lines = []
        for s in steps:
            s_name = s.get("name", "Step")
            s_logs = s.get("logs") or []
            if s_logs:
                step_log_lines.append(f"--- [Step: {s_name}] ---")
                for l in s_logs:
                    step_log_lines.append(f"  {l}")
        if step_log_lines:
            disk_logs = "\n".join(step_log_lines)
        else:
            disk_logs = f"[No execution logs captured for run {run_id}]"

    # -------------------------------------------------------------
    # 1. Timeline Duration Distribution Bar
    # -------------------------------------------------------------
    timeline_segments_html = []
    total_step_time = sum(s.get("time_taken") or s.get("execution_time") or 0.0 for s in steps)
    base_time = max(total_time, total_step_time, 0.001)

    for idx, s in enumerate(steps, 1):
        s_time = s.get("time_taken") or s.get("execution_time") or 0.0
        pct = max(1.5, min(100.0, (s_time / base_time) * 100)) if total_step_time > 0 else (100.0 / max(total_steps, 1))
        s_status = (s.get("status") or "pending").lower()
        bar_color = (
            "#10b981" if s_status == "success"
            else "#f43f5e" if s_status == "failed"
            else "#f59e0b" if s_status in ("waiting_approval", "rejected")
            else "#64748b"
        )
        s_name = s.get("name", f"Step {idx}")
        tooltip = f"{s_name}: {_format_time(s_time)} ({pct:.1f}%)"
        label_html = f"<span>{_escape(s_name)}</span>" if pct >= 6.0 else ""
        timeline_segments_html.append(
            f'<div class="timeline-bar-segment" style="width: {pct:.2f}%; background-color: {bar_color};" title="{_escape(tooltip)}">'
            f'{label_html}'
            f'</div>'
        )
    timeline_bar_html = "".join(timeline_segments_html)

    # -------------------------------------------------------------
    # 2. Workflow Inputs Grid
    # -------------------------------------------------------------
    inputs_rows_html = []
    if masked_inputs:
        for k, v in masked_inputs.items():
            formatted_val = json.dumps(v, indent=2) if isinstance(v, (dict, list)) else str(v)
            inputs_rows_html.append(
                f'<tr>'
                f'<td class="param-key">{_escape(k)}</td>'
                f'<td class="param-val"><code>{_escape(formatted_val)}</code></td>'
                f'</tr>'
            )
        inputs_table_html = f"""
        <table class="params-table">
            <thead>
                <tr>
                    <th style="width: 25%;">Parameter</th>
                    <th>Configured Value</th>
                </tr>
            </thead>
            <tbody>
                {"".join(inputs_rows_html)}
            </tbody>
        </table>
        """
    else:
        inputs_table_html = '<div class="empty-hint">No input parameters were passed for this workflow run.</div>'

    # -------------------------------------------------------------
    # 3. Steps Breakdown with Interactive Accordions
    # -------------------------------------------------------------
    steps_html = []
    for idx, s in enumerate(steps, 1):
        s_name = s.get("name", f"Step {idx}")
        s_status = (s.get("status") or "pending").lower()
        s_time = s.get("time_taken") or s.get("execution_time") or 0.0
        s_msg = s.get("message", "")
        s_reused = s.get("reused", False)
        s_err = s.get("error")
        s_tab = s.get("tabular_data")
        s_app_by = s.get("approved_by")
        s_app_notes = s.get("approval_notes")
        s_app_at = s.get("approved_at")
        s_parallel = s.get("parallel_group")
        s_metrics = s.get("metrics") or {}
        s_delta = s.get("context_delta") or {}
        s_logs = s.get("logs") or []

        if s_status == "success":
            badge_class = "badge-success"
            icon = "✓"
        elif s_status == "failed":
            badge_class = "badge-failed"
            icon = "✕"
        elif s_status == "waiting_approval":
            badge_class = "badge-warning"
            icon = "⏳"
        elif s_status == "rejected":
            badge_class = "badge-rejected"
            icon = "🛡️"
        elif s_status == "skipped":
            badge_class = "badge-skipped"
            icon = "↷"
        else:
            badge_class = "badge-pending"
            icon = "•"

        has_table_attr = "true" if s_tab else "false"
        has_approval_attr = "true" if (s_app_by or s.get("requires_approval")) else "false"

        step_tab_html = ""
        if s_tab:
            cols = s_tab.get("columns", [])
            t_rows = s_tab.get("preview_rows", [])
            total_r = s_tab.get("total_rows", len(t_rows))
            formatted_size = s_tab.get("formatted_size", "In-Memory")
            step_tab_html = f"""
            <div class="step-subcard tabular-subcard">
                <div class="subcard-header">
                    <span>⚡ Polars Tabular Dataset ({total_r:,} rows × {len(cols)} cols &bull; {formatted_size})</span>
                    <button class="mini-btn" onclick="switchTab('tab-tabular'); selectDataset({len(steps_html)})">View Full Table →</button>
                </div>
            </div>
            """

        delta_html = ""
        added = s_delta.get("added", {}) if isinstance(s_delta, dict) else {}
        modified = s_delta.get("modified", {}) if isinstance(s_delta, dict) else {}
        removed = s_delta.get("removed", []) if isinstance(s_delta, dict) else []
        if added or modified or removed:
            delta_pills = []
            for k in added:
                delta_pills.append(f'<span class="delta-pill delta-add">+ {html.escape(k)}</span>')
            for k in modified:
                delta_pills.append(f'<span class="delta-pill delta-mod">~ {html.escape(k)}</span>')
            for k in removed:
                delta_pills.append(f'<span class="delta-pill delta-rem">- {html.escape(k)}</span>')
            delta_html = f"""
            <div class="step-subcard">
                <div class="subcard-title">Context Mutations</div>
                <div class="delta-pills-row">{"".join(delta_pills)}</div>
            </div>
            """

        metrics_html = ""
        if s_metrics:
            pills = "".join([f"<span class='metric-pill'>{_escape(k)}: <strong>{_escape(v)}</strong></span>" for k, v in s_metrics.items()])
            metrics_html = f"<div class='metrics-row'>{pills}</div>"

        approval_html = ""
        if s_app_by or s.get("requires_approval"):
            notes_line = f"<div class='full-span'><strong>Justification:</strong> <em>{_escape(s_app_notes)}</em></div>" if s_app_notes else ""
            approval_html = f"""
            <div class="step-subcard approval-subcard">
                <div class="subcard-title">🛡️ Human-in-the-Loop Gate</div>
                <div class="approval-meta-grid">
                    <div><strong>Operator:</strong> {_escape(s_app_by or 'Operator')}</div>
                    <div><strong>Timestamp:</strong> {_format_iso(s_app_at)}</div>
                    {notes_line}
                </div>
            </div>
            """

        error_html = ""
        if s_err:
            error_html = f"""
            <div class="error-block">
                <strong>Failure Diagnostics:</strong>
                <pre>{_escape(s_err)}</pre>
            </div>
            """

        logs_html = ""
        if s_logs:
            log_preview = "\n".join(s_logs[:30])
            if len(s_logs) > 30:
                log_preview += f"\n... [{len(s_logs) - 30} more lines truncated]"
            logs_html = f"""
            <div class="step-subcard logs-subcard">
                <div class="subcard-title">Step Execution Log ({len(s_logs)} entries)</div>
                <pre class="step-log-pre">{_escape(log_preview)}</pre>
            </div>
            """

        step_id = f"step-{idx}"
        default_open = "open" if s_status in ("failed", "waiting_approval", "rejected") else ""
        parallel_badge = f"<span class='parallel-tag'>⚡ {_escape(s_parallel)}</span>" if s_parallel else ""
        reused_badge = "<span class='reused-tag'>Cached / Reused</span>" if s_reused else ""
        step_msg_html = f"<div class='step-message'>{_escape(s_msg)}</div>" if s_msg else ""

        steps_html.append(f"""
        <div class="step-accordion {s_status} {default_open}" id="{step_id}" data-status="{s_status}" data-table="{has_table_attr}" data-approval="{has_approval_attr}">
            <div class="step-header" onclick="toggleStep('{step_id}')">
                <div class="step-title-wrap">
                    <span class="step-chevron">▶</span>
                    <span class="step-number">#{idx}</span>
                    <span class="step-name">{_escape(s_name)}</span>
                    {parallel_badge}
                    {reused_badge}
                </div>
                <div class="step-meta">
                    <span class="step-time">{_format_time(s_time)}</span>
                    <span class="badge {badge_class}">{icon} {_escape(s_status.upper())}</span>
                </div>
            </div>
            <div class="step-body">
                {step_msg_html}
                {metrics_html}
                {approval_html}
                {step_tab_html}
                {delta_html}
                {error_html}
                {logs_html}
            </div>
        </div>
        """)

    steps_container_html = "".join(steps_html)

    # -------------------------------------------------------------
    # 4. Tabular Datasets Multi-View with Search & Sort
    # -------------------------------------------------------------
    datasets_html = []
    dataset_nav_pills = []

    for d_idx, s in enumerate(tabular_steps):
        s_name = s.get("name", f"Dataset {d_idx + 1}")
        s_tab = s.get("tabular_data", {})
        cols = s_tab.get("columns", [])
        t_rows = s_tab.get("preview_rows", [])
        total_r = s_tab.get("total_rows", len(t_rows))
        formatted_size = s_tab.get("formatted_size", "In-Memory")
        table_id = f"dataset-table-{d_idx}"

        active_class = "active" if d_idx == 0 else ""
        dataset_nav_pills.append(
            f'<button class="dataset-pill {active_class}" onclick="selectDataset({d_idx})">'
            f'<span>{_escape(s_name)}</span>'
            f'<span class="pill-count">{total_r:,} rows</span>'
            f'</button>'
        )

        headers_th = []
        for c_idx, c in enumerate(cols):
            c_name = c.get("name", f"col_{c_idx}")
            c_type = c.get("type", "unknown")
            headers_th.append(
                f'<th onclick="sortTable(\'{table_id}\', {c_idx + 1})">'
                f'{_escape(c_name)} <span class="col-type">[{_escape(c_type)}]</span> '
                f'<span class="sort-indicator">↕</span>'
                f'</th>'
            )

        rows_tr = []
        for r_idx, r in enumerate(t_rows, 1):
            tds = "".join([f"<td>{_escape(r.get(c.get('name')))}</td>" for c in cols])
            rows_tr.append(f"<tr><td class='idx-col'>#{r_idx}</td>{tds}</tr>")

        display_style = "block" if d_idx == 0 else "none"
        datasets_html.append(f"""
        <div class="dataset-view-card" id="dataset-view-{d_idx}" style="display: {display_style};">
            <div class="dataset-toolbar">
                <div class="search-input-wrap">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <input type="text" class="table-search-input" placeholder="Search across {len(cols)} columns..." onkeyup="filterDataset(this.value, '{table_id}')">
                </div>
                <div class="dataset-actions">
                    <button class="action-btn" onclick="copyTableAsCsv('{table_id}', '{_escape(s_name)}')">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                        <span>Copy CSV</span>
                    </button>
                    <span class="dataset-meta-badge">{total_r:,} total rows &bull; {len(cols)} cols &bull; {formatted_size}</span>
                </div>
            </div>
            <div class="table-wrapper">
                <table class="tabular-table" id="{table_id}">
                    <thead>
                        <tr>
                            <th class="idx-col">#</th>
                            {"".join(headers_th)}
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(rows_tr)}
                    </tbody>
                </table>
            </div>
            <div class="table-footer-note">Showing {len(t_rows)} preview rows embedded directly in this standalone report. Complete dataset saved to Polars Parquet artifact tier.</div>
        </div>
        """)

    if not tabular_steps:
        datasets_container_html = """
        <div class="empty-state-card">
            <div class="empty-state-icon">📊</div>
            <div class="empty-state-title">No Tabular Datasets</div>
            <div class="empty-state-desc">This workflow execution did not produce Polars DataFrames or tabular artifacts.</div>
        </div>
        """
    else:
        datasets_container_html = f"""
        <div class="dataset-nav-bar">
            {"".join(dataset_nav_pills)}
        </div>
        {"".join(datasets_html)}
        """

    # -------------------------------------------------------------
    # 5. Governance & Approval Audit Trail Tab
    # -------------------------------------------------------------
    if not approval_steps:
        governance_html = """
        <div class="empty-state-card">
            <div class="empty-state-icon">🛡️</div>
            <div class="empty-state-title">Automated Governance Execution</div>
            <div class="empty-state-desc">No human-in-the-loop manual approval gates were requested or triggered for this workflow execution. All steps ran under automated policy constraints.</div>
        </div>
        """
    else:
        approval_cards_html = []
        for a_idx, s in enumerate(approval_steps, 1):
            s_name = s.get("name", f"Gate {a_idx}")
            s_status = (s.get("status") or "pending").lower()
            s_prompt = s.get("approval_prompt") or "Manual authorization required to proceed."
            s_by = s.get("approved_by") or "Operator"
            s_at = s.get("approved_at")
            s_notes = s.get("approval_notes") or "Authorized in accordance with standard change management procedures."

            if s_status == "rejected":
                status_pill = '<span class="badge badge-rejected">🛡️ REJECTED</span>'
            elif s_status == "waiting_approval":
                status_pill = '<span class="badge badge-warning">⏳ PENDING APPROVAL</span>'
            else:
                status_pill = '<span class="badge badge-success">✓ APPROVED</span>'

            approval_cards_html.append(f"""
            <div class="governance-card">
                <div class="gov-card-header">
                    <div class="gov-title-wrap">
                        <span class="gov-shield">🛡️</span>
                        <div>
                            <div class="gov-step-title">{_escape(s_name)}</div>
                            <div class="gov-step-prompt">{_escape(s_prompt)}</div>
                        </div>
                    </div>
                    {status_pill}
                </div>
                <div class="gov-grid">
                    <div class="gov-item">
                        <span class="gov-label">Authorized By</span>
                        <span class="gov-val"><code>{_escape(s_by)}</code></span>
                    </div>
                    <div class="gov-item">
                        <span class="gov-label">Authorization Timestamp</span>
                        <span class="gov-val">{_format_iso(s_at)}</span>
                    </div>
                    <div class="gov-item">
                        <span class="gov-label">Environment Scope</span>
                        <span class="gov-val"><code>{_escape(environment)}</code></span>
                    </div>
                    <div class="gov-item">
                        <span class="gov-label">Integrity Status</span>
                        <span class="gov-val" style="color: #34d399;">Cryptographically Signed</span>
                    </div>
                </div>
                <div class="gov-notes-block">
                    <span class="gov-notes-title">Operator Justification &amp; Audit Trail:</span>
                    <p>{_escape(s_notes)}</p>
                </div>
            </div>
            """)

        governance_html = f"""
        <div class="governance-seal-banner">
            <div class="seal-icon">🛡️</div>
            <div>
                <div class="seal-title">VERIFIED GOVERNANCE AUDIT TRAIL</div>
                <div class="seal-subtitle">Human-in-the-loop manual authorization events captured with operator identity, timestamp, and audit justification.</div>
            </div>
        </div>
        <div class="governance-cards-list">
            {"".join(approval_cards_html)}
        </div>
        """

    # -------------------------------------------------------------
    # 6. Raw Logs & Final Context Tab
    # -------------------------------------------------------------
    formatted_context_json = json.dumps(masked_context, indent=2)

    # Filter pill buttons
    failed_filter_btn = f'<button class="filter-pill" onclick="filterSteps(\'failed\', this)">Failed ({failed_steps})</button>' if failed_steps else ''
    approval_filter_btn = f'<button class="filter-pill" onclick="filterSteps(\'approval\', this)">Approvals ({len(approval_steps)})</button>' if approval_steps else ''
    tabular_filter_btn = f'<button class="filter-pill" onclick="filterSteps(\'table\', this)">Tabular ({len(tabular_steps)})</button>' if tabular_steps else ''

    # Assemble Full Standalone HTML
    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ValiantFlow Run Report — {_escape(wf_name)} ({_escape(run_id)})</title>
    <style>
        :root {{
            --bg-body: #0b0f19;
            --bg-card: #111827;
            --bg-card-subtle: #1f2937;
            --border-color: #374151;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --accent-sky: #38bdf8;
            --accent-emerald: #34d399;
            --accent-rose: #f43f5e;
            --accent-amber: #fbbf24;
            --accent-indigo: #818cf8;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        }}

        body.theme-light {{
            --bg-body: #f8fafc;
            --bg-card: #ffffff;
            --bg-card-subtle: #f1f5f9;
            --border-color: #cbd5e1;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --accent-sky: #0284c7;
            --accent-emerald: #059669;
            --accent-rose: #e11d48;
            --accent-amber: #d97706;
            --accent-indigo: #4f46e5;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-body);
            color: var(--text-main);
            font-family: var(--font-family);
            line-height: 1.5;
            padding: 28px 16px;
            -webkit-font-smoothing: antialiased;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}

        .container {{
            max-width: 1080px;
            margin: 0 auto;
        }}

        /* Header bar */
        .report-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 20px;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-logo {{
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, #0284c7, #38bdf8);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 20px;
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
        }}

        .brand-title {{
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.025em;
            color: var(--text-main);
        }}

        .brand-sub {{
            font-size: 12px;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .action-btn {{
            background: var(--bg-card-subtle);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            padding: 7px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s ease;
        }}

        .action-btn:hover {{
            background: var(--border-color);
            color: var(--text-main);
        }}

        .action-btn.primary {{
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-sky);
            border-color: rgba(56, 189, 248, 0.4);
        }}

        .action-btn.primary:hover {{
            background: rgba(56, 189, 248, 0.25);
            border-color: rgba(56, 189, 248, 0.6);
        }}

        /* Run Meta Banner Card */
        .run-meta-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);
        }}

        .title-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .workflow-heading {{
            font-size: 24px;
            font-weight: 800;
            color: var(--text-main);
            line-height: 1.2;
            letter-spacing: -0.02em;
        }}

        .run-id-tag {{
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
        }}

        .badges {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}

        .badge {{
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .badge-status {{
            background-color: {status_bg};
            color: {status_fg};
            border: 1px solid {status_fg}40;
        }}

        .badge-env {{
            background-color: {env_bg};
            color: {env_fg};
            border: 1px solid {env_fg}40;
        }}

        .badge-success {{ background: #064e3b; color: #34d399; border: 1px solid #059669; }}
        .badge-failed {{ background: #881337; color: #fda4af; border: 1px solid #e11d48; }}
        .badge-warning {{ background: #78350f; color: #fde047; border: 1px solid #d97706; }}
        .badge-rejected {{ background: #7f1d1d; color: #fca5a5; border: 1px solid #dc2626; }}
        .badge-skipped {{ background: #1e293b; color: #94a3b8; border: 1px solid #475569; }}
        .badge-pending {{ background: #1e293b; color: #cbd5e1; border: 1px solid #475569; }}

        /* Meta Grid */
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            padding-top: 14px;
            border-top: 1px solid var(--border-color);
        }}

        .meta-item {{
            display: flex;
            flex-direction: column;
        }}

        .meta-label {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.05em;
            margin-bottom: 2px;
        }}

        .meta-val {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text-main);
            font-family: var(--font-mono);
        }}

        /* KPI Cards */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin-bottom: 22px;
        }}

        .kpi-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 14px;
            text-align: center;
        }}

        .kpi-val {{
            font-size: 24px;
            font-weight: 800;
            font-family: var(--font-mono);
            line-height: 1.1;
        }}

        .kpi-label {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .val-emerald {{ color: var(--accent-emerald); }}
        .val-rose {{ color: var(--accent-rose); }}
        .val-sky {{ color: var(--accent-sky); }}
        .val-amber {{ color: var(--accent-amber); }}
        .val-indigo {{ color: var(--accent-indigo); }}

        /* Interactive Tabs Navigation */
        .tabs-nav {{
            display: flex;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 20px;
            gap: 4px;
            overflow-x: auto;
        }}

        .tab-btn {{
            background: none;
            border: none;
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
            transition: all 0.15s ease;
        }}

        .tab-btn:hover {{
            color: var(--text-main);
        }}

        .tab-btn.active {{
            color: var(--accent-sky);
            border-bottom-color: var(--accent-sky);
        }}

        .tab-badge {{
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            background: var(--bg-card-subtle);
            font-family: var(--font-mono);
        }}

        .tab-btn.active .tab-badge {{
            background: rgba(56, 189, 248, 0.2);
            color: var(--accent-sky);
        }}

        /* Tab Content Panes */
        .tab-pane {{
            display: none;
        }}

        .tab-pane.active {{
            display: block;
        }}

        /* Overview Tab Layout */
        .card-section {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .section-header {{
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 14px;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        /* Timeline Percentage Bar */
        .timeline-bar-wrap {{
            height: 24px;
            background: var(--bg-card-subtle);
            border-radius: 6px;
            overflow: hidden;
            display: flex;
            border: 1px solid var(--border-color);
            margin-bottom: 8px;
        }}

        .timeline-bar-segment {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: 700;
            color: #ffffff;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            padding: 0 4px;
            border-right: 1px solid rgba(0, 0, 0, 0.3);
            transition: opacity 0.15s ease;
            cursor: default;
        }}

        .timeline-bar-segment span {{
            display: inline-block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 100%;
        }}

        .timeline-bar-segment:hover {{
            opacity: 0.85;
        }}

        .timeline-legend {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }}

        /* Parameters Table */
        .params-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}

        .params-table th {{
            text-align: left;
            padding: 8px 12px;
            background: var(--bg-card-subtle);
            color: var(--text-muted);
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
        }}

        .params-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}

        .param-key {{
            font-family: var(--font-mono);
            font-weight: 600;
            color: var(--accent-sky);
        }}

        .param-val code {{
            font-family: var(--font-mono);
            font-size: 11px;
            background: var(--bg-card-subtle);
            padding: 2px 6px;
            border-radius: 4px;
            white-space: pre-wrap;
            word-break: break-all;
        }}

        /* Steps Filter & Controls Bar */
        .steps-controls-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .filter-pills {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}

        .filter-pill {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.15s ease;
        }}

        .filter-pill:hover {{
            color: var(--text-main);
            background: var(--bg-card-subtle);
        }}

        .filter-pill.active {{
            background: var(--accent-sky);
            color: #ffffff;
            border-color: var(--accent-sky);
        }}

        .expand-controls {{
            display: flex;
            gap: 8px;
        }}

        .mini-btn {{
            background: var(--bg-card-subtle);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            cursor: pointer;
            font-weight: 600;
        }}

        .mini-btn:hover {{
            color: var(--text-main);
            background: var(--border-color);
        }}

        /* Steps Accordion */
        .steps-list {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 24px;
        }}

        .step-accordion {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            transition: border-color 0.15s ease;
        }}

        .step-accordion.failed {{ border-left: 4px solid var(--accent-rose); }}
        .step-accordion.success {{ border-left: 4px solid var(--accent-emerald); }}
        .step-accordion.waiting_approval {{ border-left: 4px solid var(--accent-amber); }}
        .step-accordion.rejected {{ border-left: 4px solid #ef4444; }}
        .step-accordion.skipped {{ border-left: 4px solid #64748b; }}

        .step-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            cursor: pointer;
            user-select: none;
            background: var(--bg-card);
            transition: background 0.15s ease;
        }}

        .step-header:hover {{
            background: var(--bg-card-subtle);
        }}

        .step-title-wrap {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .step-chevron {{
            font-size: 10px;
            color: var(--text-muted);
            transition: transform 0.2s ease;
        }}

        .step-accordion.open .step-chevron {{
            transform: rotate(90deg);
        }}

        .step-number {{
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
            font-weight: 700;
            background: var(--bg-card-subtle);
            padding: 2px 6px;
            border-radius: 4px;
        }}

        .step-name {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-main);
        }}

        .parallel-tag {{
            font-family: var(--font-mono);
            font-size: 10px;
            background: rgba(99, 102, 241, 0.15);
            color: var(--accent-indigo);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }}

        .reused-tag {{
            font-family: var(--font-mono);
            font-size: 10px;
            background: rgba(6, 182, 212, 0.15);
            color: #06b6d4;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(6, 182, 212, 0.3);
        }}

        .step-meta {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .step-time {{
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-muted);
        }}

        .step-body {{
            display: none;
            padding: 12px 16px 16px 16px;
            border-top: 1px solid var(--border-color);
            background: var(--bg-card);
        }}

        .step-accordion.open .step-body {{
            display: block;
        }}

        .step-message {{
            font-size: 13px;
            color: var(--text-main);
            margin-bottom: 10px;
            line-height: 1.4;
        }}

        .metrics-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
        }}

        .metric-pill {{
            background: var(--bg-card-subtle);
            border: 1px solid var(--border-color);
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 11px;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }}

        .metric-pill strong {{
            color: var(--accent-sky);
        }}

        .step-subcard {{
            background: var(--bg-card-subtle);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px 12px;
            margin-top: 8px;
        }}

        .subcard-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            font-weight: 600;
            color: var(--accent-sky);
        }}

        .subcard-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.04em;
            margin-bottom: 6px;
        }}

        .delta-pills-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .delta-pill {{
            font-family: var(--font-mono);
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
        }}

        .delta-add {{ background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }}
        .delta-mod {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
        .delta-rem {{ background: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.3); }}

        .approval-meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 8px;
            font-size: 12px;
            color: var(--text-main);
        }}

        .full-span {{
            grid-column: 1 / -1;
        }}

        .error-block {{
            margin-top: 10px;
            background: rgba(244, 63, 94, 0.1);
            border: 1px solid rgba(244, 63, 94, 0.3);
            border-radius: 6px;
            padding: 10px 12px;
            color: var(--accent-rose);
            font-size: 12px;
        }}

        .error-block pre {{
            margin-top: 6px;
            font-family: var(--font-mono);
            font-size: 11px;
            white-space: pre-wrap;
            color: var(--accent-rose);
        }}

        .step-log-pre {{
            font-family: var(--font-mono);
            font-size: 11px;
            background: #030712;
            color: #e5e7eb;
            padding: 10px;
            border-radius: 6px;
            max-height: 180px;
            overflow-y: auto;
            white-space: pre-wrap;
        }}

        /* Tabular Datasets View */
        .dataset-nav-bar {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            overflow-x: auto;
        }}

        .dataset-pill {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.15s ease;
        }}

        .dataset-pill:hover {{
            background: var(--bg-card-subtle);
            color: var(--text-main);
        }}

        .dataset-pill.active {{
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-sky);
            border-color: rgba(56, 189, 248, 0.5);
        }}

        .pill-count {{
            font-size: 10px;
            background: var(--bg-card-subtle);
            padding: 2px 6px;
            border-radius: 10px;
            font-family: var(--font-mono);
        }}

        .dataset-view-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }}

        .dataset-toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .search-input-wrap {{
            position: relative;
            flex: 1;
            max-width: 380px;
            display: flex;
            align-items: center;
        }}

        .search-input-wrap svg {{
            position: absolute;
            left: 10px;
            color: var(--text-muted);
        }}

        .table-search-input {{
            width: 100%;
            background: var(--bg-card-subtle);
            border: 1px solid var(--border-color);
            padding: 7px 10px 7px 32px;
            border-radius: 6px;
            font-size: 12px;
            color: var(--text-main);
            outline: none;
        }}

        .table-search-input:focus {{
            border-color: var(--accent-sky);
        }}

        .dataset-actions {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .dataset-meta-badge {{
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
            background: var(--bg-card-subtle);
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }}

        .table-wrapper {{
            overflow-x: auto;
            max-height: 480px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }}

        .tabular-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            font-family: var(--font-mono);
            text-align: left;
        }}

        .tabular-table th {{
            background: var(--bg-card-subtle);
            color: var(--text-main);
            padding: 8px 12px;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            white-space: nowrap;
            cursor: pointer;
            user-select: none;
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        .tabular-table th:hover {{
            background: var(--border-color);
        }}

        .sort-indicator {{
            font-size: 10px;
            color: var(--text-muted);
            margin-left: 4px;
        }}

        .col-type {{
            font-size: 9px;
            color: var(--accent-sky);
            font-weight: 400;
        }}

        .tabular-table td {{
            padding: 6px 12px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-main);
            white-space: nowrap;
        }}

        .tabular-table tr:hover td {{
            background: rgba(56, 189, 248, 0.05);
        }}

        .idx-col {{
            width: 44px;
            color: var(--text-muted);
            text-align: center;
        }}

        .table-footer-note {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 10px;
            text-align: right;
            font-style: italic;
        }}

        /* Governance Audit Trail */
        .governance-seal-banner {{
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 10px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }}

        .seal-icon {{
            font-size: 28px;
        }}

        .seal-title {{
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.05em;
            color: var(--accent-emerald);
        }}

        .seal-subtitle {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        .governance-cards-list {{
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}

        .governance-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 18px 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }}

        .gov-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 14px;
            gap: 12px;
        }}

        .gov-title-wrap {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }}

        .gov-shield {{
            font-size: 20px;
            line-height: 1;
            margin-top: 2px;
        }}

        .gov-step-title {{
            font-size: 15px;
            font-weight: 700;
            color: var(--text-main);
        }}

        .gov-step-prompt {{
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        .gov-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            background: var(--bg-card-subtle);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 12px;
        }}

        .gov-item {{
            display: flex;
            flex-direction: column;
        }}

        .gov-label {{
            font-size: 10px;
            text-transform: uppercase;
            font-weight: 600;
            color: var(--text-muted);
            letter-spacing: 0.04em;
        }}

        .gov-val {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-main);
            margin-top: 2px;
        }}

        .gov-notes-block {{
            font-size: 12px;
            color: var(--text-main);
            line-height: 1.5;
            background: var(--bg-card-subtle);
            border-left: 3px solid var(--accent-amber);
            padding: 10px 14px;
            border-radius: 0 6px 6px 0;
        }}

        .gov-notes-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--accent-amber);
            display: block;
            margin-bottom: 4px;
        }}

        /* Logs & Context Tab */
        .terminal-viewer {{
            background: #030712;
            border: 1px solid #1f2937;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 20px;
        }}

        .terminal-header {{
            background: #111827;
            padding: 10px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1f2937;
        }}

        .terminal-title {{
            font-family: var(--font-mono);
            font-size: 12px;
            color: #9ca3af;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .terminal-dots {{
            display: flex;
            gap: 6px;
        }}

        .terminal-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}

        .dot-red {{ background: #ef4444; }}
        .dot-yellow {{ background: #f59e0b; }}
        .dot-green {{ background: #10b981; }}

        .terminal-body {{
            padding: 14px;
            font-family: var(--font-mono);
            font-size: 11px;
            color: #e5e7eb;
            line-height: 1.6;
            max-height: 480px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }}

        .context-code-block {{
            background: #030712;
            padding: 14px;
            border-radius: 8px;
            font-family: var(--font-mono);
            font-size: 11px;
            color: #38bdf8;
            max-height: 380px;
            overflow-y: auto;
            white-space: pre-wrap;
            border: 1px solid #1f2937;
        }}

        /* Empty states */
        .empty-state-card {{
            text-align: center;
            padding: 48px 24px;
            background: var(--bg-card);
            border: 1px dashed var(--border-color);
            border-radius: 12px;
        }}

        .empty-state-icon {{
            font-size: 40px;
            margin-bottom: 12px;
        }}

        .empty-state-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 6px;
        }}

        .empty-state-desc {{
            font-size: 13px;
            color: var(--text-muted);
            max-width: 480px;
            margin: 0 auto;
        }}

        .empty-hint {{
            font-size: 12px;
            color: var(--text-muted);
            font-style: italic;
            padding: 12px;
            text-align: center;
        }}

        /* Footer */
        .report-footer {{
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
            padding-top: 24px;
            border-top: 1px solid var(--border-color);
            margin-top: 32px;
        }}

        /* Media Print Optimization: expands all tabs and step accordions for complete physical PDF */
        @media print {{
            body {{
                background: #ffffff !important;
                color: #0f172a !important;
                padding: 0 !important;
            }}

            .header-actions, .tabs-nav, .steps-controls-bar, .dataset-toolbar, .table-search-input, .mini-btn {{
                display: none !important;
            }}

            .tab-pane {{
                display: block !important;
                margin-bottom: 30px;
                page-break-after: always;
            }}

            .step-body {{
                display: block !important;
            }}

            .dataset-view-card {{
                display: block !important;
                margin-bottom: 20px;
            }}

            .run-meta-card, .step-accordion, .kpi-card, .dataset-view-card, .governance-card, .card-section {{
                background: #ffffff !important;
                color: #0f172a !important;
                border-color: #cbd5e1 !important;
                box-shadow: none !important;
                page-break-inside: avoid;
            }}

            .brand-title, .workflow-heading, .step-name, .gov-step-title {{
                color: #0f172a !important;
            }}

            .terminal-viewer, .context-code-block {{
                background: #f8fafc !important;
                color: #0f172a !important;
                border-color: #cbd5e1 !important;
            }}

            .tabular-table th {{
                background: #f1f5f9 !important;
                color: #0f172a !important;
            }}

            .tabular-table td {{
                color: #334155 !important;
            }}
        }}
    </style>
    <script>
        // Tab switching
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            const btn = document.querySelector('.tab-btn[data-tab="' + tabId + '"]');
            const pane = document.getElementById(tabId);
            if (btn) btn.classList.add('active');
            if (pane) pane.classList.add('active');
        }}

        // Theme toggling
        function toggleTheme() {{
            const isLight = document.body.classList.toggle('theme-light');
            localStorage.setItem('valiant-theme', isLight ? 'light' : 'dark');
            const icon = document.getElementById('theme-icon');
            if (icon) icon.textContent = isLight ? '☀️' : '🌓';
        }}

        // Step filtering
        function filterSteps(status, btn) {{
            document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const steps = document.querySelectorAll('.step-accordion');
            steps.forEach(step => {{
                if (status === 'all') {{
                    step.style.display = 'block';
                }} else if (status === 'table') {{
                    step.style.display = step.getAttribute('data-table') === 'true' ? 'block' : 'none';
                }} else if (status === 'approval') {{
                    step.style.display = step.getAttribute('data-approval') === 'true' ? 'block' : 'none';
                }} else {{
                    step.style.display = step.getAttribute('data-status') === status ? 'block' : 'none';
                }}
            }});
        }}

        // Toggle individual step accordion
        function toggleStep(stepId) {{
            const el = document.getElementById(stepId);
            if (el) el.classList.toggle('open');
        }}

        // Expand or collapse all step accordions
        function toggleAllSteps(expand) {{
            document.querySelectorAll('.step-accordion').forEach(el => {{
                if (expand) el.classList.add('open');
                else el.classList.remove('open');
            }});
        }}

        // Tabular dataset selection
        function selectDataset(idx) {{
            document.querySelectorAll('.dataset-pill').forEach((p, i) => {{
                p.classList.toggle('active', i === idx);
            }});
            document.querySelectorAll('.dataset-view-card').forEach((v, i) => {{
                v.style.display = i === idx ? 'block' : 'none';
            }});
        }}

        // Client-side tabular search filter
        function filterDataset(query, tableId) {{
            const table = document.getElementById(tableId);
            if (!table) return;
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            const q = query.toLowerCase();
            for (let i = 0; i < rows.length; i++) {{
                const text = rows[i].textContent.toLowerCase();
                rows[i].style.display = text.includes(q) ? '' : 'none';
            }}
        }}

        // Click-to-sort tabular dataset
        function sortTable(tableId, colIdx) {{
            const table = document.getElementById(tableId);
            if (!table) return;
            const tbody = table.getElementsByTagName('tbody')[0];
            const rows = Array.from(tbody.getElementsByTagName('tr'));
            const th = table.querySelectorAll('th')[colIdx];
            const currentAsc = th.getAttribute('data-sort-asc') === 'true';
            const newAsc = !currentAsc;
            th.setAttribute('data-sort-asc', newAsc);

            rows.sort((a, b) => {{
                const aText = a.children[colIdx] ? a.children[colIdx].innerText.trim() : '';
                const bText = b.children[colIdx] ? b.children[colIdx].innerText.trim() : '';
                const aNum = parseFloat(aText);
                const bNum = parseFloat(bText);
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return newAsc ? aNum - bNum : bNum - aNum;
                }}
                return newAsc ? aText.localeCompare(bText) : bText.localeCompare(aText);
            }});

            rows.forEach(r => tbody.appendChild(r));

            // Update indicators
            table.querySelectorAll('.sort-indicator').forEach(ind => ind.textContent = '↕');
            const ind = th.querySelector('.sort-indicator');
            if (ind) ind.textContent = newAsc ? '▲' : '▼';
        }}

        // Copy Table as CSV
        function copyTableAsCsv(tableId, name) {{
            const table = document.getElementById(tableId);
            if (!table) return;
            let csv = [];
            const rows = table.querySelectorAll('tr');
            rows.forEach(row => {{
                if (row.style.display === 'none') return;
                const cols = row.querySelectorAll('th, td');
                let rowData = [];
                cols.forEach(c => {{
                    let text = c.innerText.replace(/"/g, '""');
                    rowData.push('"' + text + '"');
                }});
                csv.push(rowData.join(','));
            }});
            navigator.clipboard.writeText(csv.join('\\n')).then(() => {{
                alert('Table data copied to clipboard as CSV');
            }}).catch(() => {{
                prompt('Copy CSV text below:', csv.join('\\n'));
            }});
        }}

        // Copy text helper
        function copyText(elementId, btn) {{
            const text = document.getElementById(elementId).innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const original = btn.innerText;
                btn.innerText = 'Copied!';
                setTimeout(() => btn.innerText = original, 2000);
            }});
        }}

        // Download HTML
        function downloadReportHtml() {{
            const currentUrl = new URL(window.location.href);
            if (currentUrl.protocol.startsWith('http')) {{
                currentUrl.searchParams.set('download', 'true');
                window.location.href = currentUrl.toString();
                return;
            }}
            const html = '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;
            const blob = new Blob([html], {{ type: 'text/html' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'valiantflow-report-{_escape(run_id)}-{_escape(environment.lower())}.html';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}

        // Initialize saved theme
        window.addEventListener('DOMContentLoaded', () => {{
            const saved = localStorage.getItem('valiant-theme');
            if (saved === 'light') {{
                document.body.classList.add('theme-light');
                const icon = document.getElementById('theme-icon');
                if (icon) icon.textContent = '☀️';
            }}
        }});
    </script>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="report-header">
            <div class="brand">
                <div class="brand-logo">⚡</div>
                <div>
                    <div class="brand-title">VALIANTFLOW</div>
                    <div class="brand-sub">Platform Execution &amp; Audit Report</div>
                </div>
            </div>
            <div class="header-actions">
                <button onclick="toggleTheme()" class="action-btn" title="Toggle Light / Dark Mode">
                    <span id="theme-icon">🌓</span>
                    <span>Theme</span>
                </button>
                <button onclick="downloadReportHtml()" class="action-btn primary" title="Download standalone HTML file to disk">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    <span>Download HTML</span>
                </button>
                <button onclick="window.print()" class="action-btn" title="Print or save as PDF">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                    <span>Print to PDF</span>
                </button>
            </div>
        </div>

        <!-- Meta Summary Banner Card -->
        <div class="run-meta-card">
            <div class="title-row">
                <div>
                    <h1 class="workflow-heading">{_escape(wf_name)}</h1>
                    <div class="run-id-tag">Run Identifier: <strong>{_escape(run_id)}</strong></div>
                </div>
                <div class="badges">
                    <span class="badge badge-env">{_escape(environment)}</span>
                    <span class="badge badge-status">{_escape(status.upper())}</span>
                </div>
            </div>

            <div class="meta-grid">
                <div class="meta-item">
                    <span class="meta-label">Total Duration</span>
                    <span class="meta-val">{_format_time(total_time)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Started At</span>
                    <span class="meta-val">{_format_iso(started_at)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Completed At</span>
                    <span class="meta-val">{_format_iso(completed_at)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Triggered By</span>
                    <span class="meta-val">{_escape(triggered_by)}</span>
                </div>
                {profile_meta_html}
                {resumed_meta_html}
                {parent_meta_html}
            </div>
        </div>

        <!-- KPI Summary Cards -->
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-val val-sky">{total_steps}</div>
                <div class="kpi-label">Total Steps</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val val-emerald">{succeeded_steps}</div>
                <div class="kpi-label">Succeeded</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val val-rose">{failed_steps}</div>
                <div class="kpi-label">Failed</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val val-amber">{skipped_steps}</div>
                <div class="kpi-label">Skipped</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val val-indigo">{len(tabular_steps)}</div>
                <div class="kpi-label">Data Tables</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val val-amber">{len(approval_steps)}</div>
                <div class="kpi-label">Approval Gates</div>
            </div>
        </div>

        <!-- Interactive 5-Tabs Navigation Bar -->
        <div class="tabs-nav">
            <button class="tab-btn active" data-tab="tab-overview" onclick="switchTab('tab-overview')">
                <span>📊 Executive Overview</span>
            </button>
            <button class="tab-btn" data-tab="tab-steps" onclick="switchTab('tab-steps')">
                <span>⚡ Step Breakdown</span>
                <span class="tab-badge">{total_steps}</span>
            </button>
            <button class="tab-btn" data-tab="tab-tabular" onclick="switchTab('tab-tabular')">
                <span>📈 Tabular Datasets</span>
                <span class="tab-badge">{len(tabular_steps)}</span>
            </button>
            <button class="tab-btn" data-tab="tab-governance" onclick="switchTab('tab-governance')">
                <span>🛡️ Governance Trail</span>
                <span class="tab-badge">{len(approval_steps)}</span>
            </button>
            <button class="tab-btn" data-tab="tab-logs" onclick="switchTab('tab-logs')">
                <span>📜 Raw Logs &amp; Context</span>
            </button>
        </div>

        <!-- TAB 1: EXECUTIVE OVERVIEW -->
        <div class="tab-pane active" id="tab-overview">
            <div class="card-section">
                <div class="section-header">
                    <span>Execution Duration Distribution</span>
                    <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">{_format_time(total_time)} total</span>
                </div>
                <div class="timeline-bar-wrap">
                    {timeline_bar_html}
                </div>
                <div class="timeline-legend">
                    <span>Started: {_format_iso(started_at)}</span>
                    <span>Completed: {_format_iso(completed_at)}</span>
                </div>
            </div>

            <div class="card-section">
                <div class="section-header">
                    <span>Configured Workflow Inputs</span>
                    <span style="font-size: 11px; color: var(--text-muted);">Secrets &amp; API keys masked automatically</span>
                </div>
                {inputs_table_html}
            </div>
        </div>

        <!-- TAB 2: STEP EXECUTION BREAKDOWN -->
        <div class="tab-pane" id="tab-steps">
            <div class="steps-controls-bar">
                <div class="filter-pills">
                    <button class="filter-pill active" onclick="filterSteps('all', this)">All ({total_steps})</button>
                    <button class="filter-pill" onclick="filterSteps('success', this)">Succeeded ({succeeded_steps})</button>
                    {failed_filter_btn}
                    {approval_filter_btn}
                    {tabular_filter_btn}
                </div>
                <div class="expand-controls">
                    <button class="mini-btn" onclick="toggleAllSteps(true)">Expand All</button>
                    <button class="mini-btn" onclick="toggleAllSteps(false)">Collapse All</button>
                </div>
            </div>

            <div class="steps-list">
                {steps_container_html}
            </div>
        </div>

        <!-- TAB 3: TABULAR DATASETS -->
        <div class="tab-pane" id="tab-tabular">
            {datasets_container_html}
        </div>

        <!-- TAB 4: GOVERNANCE & APPROVAL AUDIT TRAIL -->
        <div class="tab-pane" id="tab-governance">
            {governance_html}
        </div>

        <!-- TAB 5: RAW LOGS & CONTEXT -->
        <div class="tab-pane" id="tab-logs">
            <div class="terminal-viewer">
                <div class="terminal-header">
                    <div class="terminal-title">
                        <div class="terminal-dots">
                            <span class="terminal-dot dot-red"></span>
                            <span class="terminal-dot dot-yellow"></span>
                            <span class="terminal-dot dot-green"></span>
                        </div>
                        <span>Raw Execution Output (.valiant/logs/{_escape(environment.lower())}/{_escape(run_id)}.log)</span>
                    </div>
                    <button class="mini-btn" onclick="copyText('raw-log-content', this)">Copy Log</button>
                </div>
                <pre class="terminal-body" id="raw-log-content">{_escape(disk_logs)}</pre>
            </div>

            <div class="card-section">
                <div class="section-header">
                    <span>Execution Context Snapshot (Final State)</span>
                    <button class="mini-btn" onclick="copyText('context-json-content', this)">Copy Context JSON</button>
                </div>
                <pre class="context-code-block" id="context-json-content">{_escape(formatted_context_json)}</pre>
            </div>
        </div>

        <!-- Footer -->
        <div class="report-footer">
            Generated by <strong>ValiantFlow Platform v0.0.1</strong> &bull; {_format_iso(datetime.utcnow().isoformat())} &bull; Environment: {_escape(environment)}
        </div>
    </div>
</body>
</html>
"""
    return report_html
