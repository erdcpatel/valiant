"""
Valiant HTML Report Generator: Self-contained, executive-grade standalone HTML reports
for workflow execution review, compliance audits, and stakeholder sharing.
Includes embedded responsive styling, dark-mode & print-friendly CSS, Polars tabular data,
and human-in-the-loop approval audit trails.
"""
from typing import Dict, Any, Optional, List
import html
import json
from datetime import datetime


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
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M:%S UTC")
    except Exception:
        return str(iso_str)


def generate_run_html_report(run_data: Dict[str, Any], env: str = "dev") -> str:
    """
    Generate a complete, self-contained HTML report from a workflow run dictionary.
    Requires ZERO external CDN dependencies, script tags, or remote assets.
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
    steps: List[Dict[str, Any]] = run_data.get("steps") or run_data.get("results") or []

    # KPI counts
    total_steps = len(steps)
    succeeded_steps = sum(1 for s in steps if s.get("status") == "success" or s.get("success"))
    failed_steps = sum(1 for s in steps if s.get("status") == "failed")
    skipped_steps = sum(1 for s in steps if s.get("status") == "skipped")
    waiting_steps = sum(1 for s in steps if s.get("status") == "waiting_approval")
    rejected_steps = sum(1 for s in steps if s.get("status") == "rejected")
    reused_steps = sum(1 for s in steps if s.get("reused"))

    # Check if any step produced tabular data
    tabular_steps = [s for s in steps if s.get("tabular_data")]

    # Check if any step required approval
    approval_steps = [s for s in steps if s.get("requires_approval") or s.get("approved_by") or s.get("status") in ("waiting_approval", "rejected")]

    # Status badge color
    status_bg = "#064e3b" if status == "completed" and success else "#881337" if status == "failed" else "#78350f" if status == "waiting_approval" else "#334155"
    status_fg = "#34d399" if status == "completed" and success else "#fda4af" if status == "failed" else "#fde047" if status == "waiting_approval" else "#94a3b8"

    # Environment color
    env_bg = "#064e3b" if environment == "DEV" else "#78350f" if environment == "UAT" else "#881337"
    env_fg = "#34d399" if environment == "DEV" else "#fde047" if environment == "UAT" else "#fda4af"

    # Generate Steps HTML
    steps_html = []
    for idx, s in enumerate(steps, 1):
        s_name = s.get("name", f"Step {idx}")
        s_status = (s.get("status") or "pending").lower()
        s_time = s.get("time_taken", 0.0)
        s_msg = s.get("message", "")
        s_reused = s.get("reused", False)
        s_err = s.get("error")
        s_tab = s.get("tabular_data")
        s_app_by = s.get("approved_by")
        s_app_notes = s.get("approval_notes")
        s_app_at = s.get("approved_at")
        s_parallel = s.get("parallel_group")
        s_metrics = s.get("metrics") or {}

        # Status badge styling
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

        tabular_preview_html = ""
        if s_tab:
            cols = s_tab.get("columns", [])
            t_rows = s_tab.get("preview_rows", [])
            total_r = s_tab.get("total_rows", len(t_rows))
            formatted_size = s_tab.get("formatted_size", "In-Memory")
            
            headers_th = "".join([f"<th>{_escape(c.get('name'))} <span class='col-type'>[{_escape(c.get('type'))}]</span></th>" for c in cols])
            rows_tr = []
            for r_idx, r in enumerate(t_rows[:15], 1):
                tds = "".join([f"<td>{_escape(r.get(c.get('name')))}</td>" for c in cols])
                rows_tr.append(f"<tr><td class='idx-col'>#{r_idx}</td>{tds}</tr>")
            
            tabular_preview_html = f"""
            <div class="tabular-card">
                <div class="tabular-header">
                    <span class="tabular-title">⚡ Polars Tabular Dataset ({total_r:,} total rows × {len(cols)} columns &bull; {formatted_size})</span>
                    <span class="tabular-badge">Previewing first {len(t_rows)} rows</span>
                </div>
                <div class="table-wrapper">
                    <table class="tabular-table">
                        <thead>
                            <tr>
                                <th class="idx-col">#</th>
                                {headers_th}
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(rows_tr)}
                        </tbody>
                    </table>
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

        approval_html = ""
        if s_app_by or s.get("requires_approval"):
            approval_html = f"""
            <div class="approval-card">
                <span class="approval-tag">🛡️ Human-in-the-Loop Gate</span>
                <div class="approval-details">
                    <span><strong>Approver:</strong> {_escape(s_app_by or 'Operator')}</span>
                    <span><strong>Timestamp:</strong> {_format_iso(s_app_at)}</span>
                    {f"<span><strong>Notes:</strong> <em>{_escape(s_app_notes)}</em></span>" if s_app_notes else ""}
                </div>
            </div>
            """

        metrics_html = ""
        if s_metrics:
            pills = "".join([f"<span class='metric-pill'>{_escape(k)}: <strong>{_escape(v)}</strong></span>" for k, v in s_metrics.items()])
            metrics_html = f"<div class='metrics-row'>{pills}</div>"

        steps_html.append(f"""
        <div class="step-card {s_status}">
            <div class="step-header">
                <div class="step-title-wrap">
                    <span class="step-number">#{idx}</span>
                    <span class="step-name">{_escape(s_name)}</span>
                    {f"<span class='parallel-tag'>⚡ {_escape(s_parallel)}</span>" if s_parallel else ""}
                    {f"<span class='reused-tag'>Cached / Reused</span>" if s_reused else ""}
                </div>
                <div class="step-meta">
                    <span class="step-time">{_format_time(s_time)}</span>
                    <span class="badge {badge_class}">{icon} {_escape(s_status.upper())}</span>
                </div>
            </div>
            {f"<div class='step-message'>{_escape(s_msg)}</div>" if s_msg else ""}
            {metrics_html}
            {approval_html}
            {tabular_preview_html}
            {error_html}
        </div>
        """)

    steps_container_html = "".join(steps_html)

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Valiant Run Report — {_escape(wf_name)} ({_escape(run_id)})</title>
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
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
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
            padding: 32px 16px;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 1040px;
            margin: 0 auto;
        }}

        /* Header bar */
        .report-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 24px;
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
            color: #0b0f19;
        }}

        .brand-title {{
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.025em;
            color: #ffffff;
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
            background: #1f2937;
            color: #f3f4f6;
            border: 1px solid var(--border-color);
            padding: 7px 15px;
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
            background: #374151;
            color: #ffffff;
        }}

        .action-btn.primary {{
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border-color: rgba(56, 189, 248, 0.4);
        }}

        .action-btn.primary:hover {{
            background: rgba(56, 189, 248, 0.25);
            color: #7dd3fc;
            border-color: rgba(56, 189, 248, 0.6);
        }}

        /* Main Run Meta Card */
        .run-meta-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
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
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.2;
            letter-spacing: -0.02em;
        }}

        .run-id-tag {{
            font-family: var(--font-mono);
            font-size: 13px;
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
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            padding-top: 16px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
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
            font-size: 14px;
            font-weight: 600;
            color: #f3f4f6;
            font-family: var(--font-mono);
        }}

        /* KPI Cards */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-bottom: 28px;
        }}

        .kpi-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }}

        .kpi-val {{
            font-size: 26px;
            font-weight: 800;
            font-family: var(--font-mono);
            line-height: 1.1;
        }}

        .kpi-label {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
            font-weight: 500;
        }}

        .val-emerald {{ color: var(--accent-emerald); }}
        .val-rose {{ color: var(--accent-rose); }}
        .val-sky {{ color: var(--accent-sky); }}
        .val-amber {{ color: var(--accent-amber); }}

        /* Section Headings */
        .section-title {{
            font-size: 17px;
            font-weight: 700;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #f3f4f6;
        }}

        .section-title span {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 400;
        }}

        /* Step Cards */
        .steps-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 32px;
        }}

        .step-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px 20px;
            transition: border-color 0.15s ease;
        }}

        .step-card.failed {{ border-left: 4px solid var(--accent-rose); }}
        .step-card.success {{ border-left: 4px solid var(--accent-emerald); }}
        .step-card.waiting_approval {{ border-left: 4px solid var(--accent-amber); }}
        .step-card.rejected {{ border-left: 4px solid #ef4444; }}
        .step-card.skipped {{ border-left: 4px solid #64748b; }}

        .step-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .step-title-wrap {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .step-number {{
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
            font-weight: 700;
            background: #1f2937;
            padding: 2px 6px;
            border-radius: 4px;
        }}

        .step-name {{
            font-size: 15px;
            font-weight: 700;
            color: #ffffff;
        }}

        .parallel-tag {{
            font-family: var(--font-mono);
            font-size: 10px;
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }}

        .reused-tag {{
            font-family: var(--font-mono);
            font-size: 10px;
            background: rgba(6, 182, 212, 0.15);
            color: #67e8f9;
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

        .step-message {{
            font-size: 13px;
            color: #d1d5db;
            margin-top: 4px;
            line-height: 1.4;
        }}

        .metrics-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }}

        .metric-pill {{
            background: #1f2937;
            border: 1px solid #374151;
            padding: 2px 8px;
            border-radius: 5px;
            font-size: 11px;
            color: #9ca3af;
            font-family: var(--font-mono);
        }}

        .metric-pill strong {{
            color: #38bdf8;
        }}

        /* Approval Card */
        .approval-card {{
            margin-top: 10px;
            background: rgba(245, 158, 11, 0.08);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 8px;
            padding: 10px 14px;
        }}

        .approval-tag {{
            font-size: 11px;
            font-weight: 700;
            color: #fbbf24;
            display: block;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .approval-details {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            font-size: 12px;
            color: #e5e7eb;
        }}

        /* Tabular Preview */
        .tabular-card {{
            margin-top: 12px;
            background: #0d131f;
            border: 1px solid #1e293b;
            border-radius: 8px;
            overflow: hidden;
        }}

        .tabular-header {{
            background: #111827;
            padding: 8px 12px;
            border-bottom: 1px solid #1e293b;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .tabular-title {{
            font-size: 12px;
            font-weight: 600;
            color: #38bdf8;
            font-family: var(--font-mono);
        }}

        .tabular-badge {{
            font-size: 10px;
            color: #94a3b8;
            font-family: var(--font-mono);
        }}

        .table-wrapper {{
            overflow-x: auto;
            max-height: 280px;
        }}

        .tabular-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            font-family: var(--font-mono);
            text-align: left;
        }}

        .tabular-table th {{
            background: #1e293b;
            color: #cbd5e1;
            padding: 6px 10px;
            font-weight: 600;
            border-bottom: 1px solid #334155;
            white-space: nowrap;
        }}

        .col-type {{
            font-size: 9px;
            color: #38bdf8;
            font-weight: 400;
        }}

        .tabular-table td {{
            padding: 5px 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: #e2e8f0;
            white-space: nowrap;
        }}

        .tabular-table tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .idx-col {{
            width: 36px;
            color: #64748b;
            text-align: center;
        }}

        /* Error block */
        .error-block {{
            margin-top: 12px;
            background: rgba(244, 63, 94, 0.08);
            border: 1px solid rgba(244, 63, 94, 0.25);
            border-radius: 8px;
            padding: 10px 14px;
            color: #fda4af;
            font-size: 12px;
        }}

        .error-block pre {{
            margin-top: 6px;
            font-family: var(--font-mono);
            font-size: 11px;
            white-space: pre-wrap;
            color: #fecdd3;
        }}

        /* Footer */
        .report-footer {{
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
            padding-top: 24px;
            border-top: 1px solid var(--border-color);
        }}

        /* Media Print Optimization */
        @media print {{
            body {{
                background: #ffffff !important;
                color: #111827 !important;
                padding: 0;
            }}

            .header-actions {{
                display: none !important;
            }}

            .run-meta-card, .step-card, .kpi-card, .tabular-card {{
                background: #ffffff !important;
                color: #111827 !important;
                border-color: #e5e7eb !important;
                box-shadow: none !important;
                page-break-inside: avoid;
            }}

            .brand-title, .workflow-heading, .step-name {{
                color: #111827 !important;
            }}

            .badge-status, .badge-env {{
                border: 1px solid #111827 !important;
                color: #111827 !important;
                background: #f3f4f6 !important;
            }}

            .tabular-table th {{
                background: #f3f4f6 !important;
                color: #111827 !important;
            }}

            .tabular-table td {{
                color: #374151 !important;
            }}
        }}
    </style>
    <script>
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
            a.download = 'valiant-report-{_escape(run_id)}-{_escape(environment.lower())}.html';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
    </script>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="report-header">
            <div class="brand">
                <div class="brand-logo">⚡</div>
                <div>
                    <div class="brand-title">VALIANT</div>
                    <div class="brand-sub">Platform Execution &amp; Audit Report</div>
                </div>
            </div>
            <div class="header-actions">
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

        <!-- Meta Summary Card -->
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
                {f'<div class="meta-item"><span class="meta-label">Resumed From</span><span class="meta-val">{_escape(resumed_from)}</span></div>' if resumed_from else ''}
                {f'<div class="meta-item"><span class="meta-label">Parent Execution</span><span class="meta-val">{_escape(parent_run_id)}</span></div>' if parent_run_id else ''}
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
            {f'<div class="kpi-card"><div class="kpi-val val-sky">{len(tabular_steps)}</div><div class="kpi-label">Data Tables</div></div>' if tabular_steps else ''}
            {f'<div class="kpi-card"><div class="kpi-val val-amber">{len(approval_steps)}</div><div class="kpi-label">Approval Gates</div></div>' if approval_steps else ''}
        </div>

        <!-- Steps Timeline Section -->
        <h2 class="section-title">
            Step Execution Breakdown
            <span>({succeeded_steps}/{total_steps} Passed)</span>
        </h2>
        <div class="steps-list">
            {steps_container_html}
        </div>

        <!-- Footer -->
        <div class="report-footer">
            Generated by <strong>Valiant Platform v3.0</strong> &bull; {_format_iso(datetime.utcnow().isoformat())} &bull; Environment: {_escape(environment)}
        </div>
    </div>
</body>
</html>
"""
    return report_html
