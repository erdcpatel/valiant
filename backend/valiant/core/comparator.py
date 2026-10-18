"""
Comparator engine for computing side-by-side regression differences, latency drift,
and input/context diffs between any two workflow executions.
"""
from typing import Dict, Any, List, Optional


def compare_runs_data(run_a: Dict[str, Any], run_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute structured diff between baseline run_a and target run_b.
    """
    if not run_a or not run_b:
        return {
            "summary": {"error": "Both run_a and run_b must be provided"},
            "steps": [],
            "inputs_diff": {},
            "context_diff": {}
        }

    time_a = float(run_a.get("total_time") or 0.0)
    time_b = float(run_b.get("total_time") or 0.0)
    time_delta = round(time_b - time_a, 3)
    time_ratio = round(time_b / max(time_a, 0.001), 2) if time_a > 0 else 1.0

    success_a = bool(run_a.get("success"))
    success_b = bool(run_b.get("success"))

    if success_a and not success_b:
        outcome = "regression"
    elif not success_a and success_b:
        outcome = "improved"
    else:
        outcome = "same"

    steps_a = {s["name"]: s for s in run_a.get("steps", [])}
    steps_b = {s["name"]: s for s in run_b.get("steps", [])}

    all_step_names: List[str] = []
    for s in run_a.get("steps", []):
        if s["name"] not in all_step_names:
            all_step_names.append(s["name"])
    for s in run_b.get("steps", []):
        if s["name"] not in all_step_names:
            all_step_names.append(s["name"])

    step_comparisons: List[Dict[str, Any]] = []
    regressed_steps_count = 0
    slower_steps_count = 0

    for name in all_step_names:
        sa = steps_a.get(name)
        sb = steps_b.get(name)

        if sa and sb:
            status_a = sa.get("status")
            status_b = sb.get("status")
            st_time_a = float(sa.get("time_taken") or 0.0)
            st_time_b = float(sb.get("time_taken") or 0.0)
            st_delta = round(st_time_b - st_time_a, 3)

            ok_a = sa.get("success", False)
            ok_b = sb.get("success", False)

            if ok_a and not ok_b:
                match_type = "regressed"
                regressed_steps_count += 1
            elif not ok_a and ok_b:
                match_type = "improved"
            elif st_delta > 0.05 and st_time_b > (st_time_a * 1.2):
                match_type = "slower"
                slower_steps_count += 1
            elif st_delta < -0.05 and st_time_a > (st_time_b * 1.2):
                match_type = "faster"
            else:
                match_type = "matched"

            step_comparisons.append({
                "name": name,
                "status_a": status_a,
                "status_b": status_b,
                "success_a": ok_a,
                "success_b": ok_b,
                "time_a": st_time_a,
                "time_b": st_time_b,
                "time_delta": st_delta,
                "match_type": match_type,
                "error_a": sa.get("error"),
                "error_b": sb.get("error"),
                "message_a": sa.get("message"),
                "message_b": sb.get("message"),
            })
        elif sa and not sb:
            step_comparisons.append({
                "name": name,
                "status_a": sa.get("status"),
                "status_b": "missing",
                "success_a": sa.get("success", False),
                "success_b": False,
                "time_a": float(sa.get("time_taken") or 0.0),
                "time_b": 0.0,
                "time_delta": 0.0,
                "match_type": "missing_in_target",
                "error_a": sa.get("error"),
                "error_b": None,
                "message_a": sa.get("message"),
                "message_b": None,
            })
        else:
            step_comparisons.append({
                "name": name,
                "status_a": "missing",
                "status_b": sb.get("status") if sb else "unknown",
                "success_a": False,
                "success_b": sb.get("success", False) if sb else False,
                "time_a": 0.0,
                "time_b": float(sb.get("time_taken") or 0.0) if sb else 0.0,
                "time_delta": 0.0,
                "match_type": "new_in_target",
                "error_a": None,
                "error_b": sb.get("error") if sb else None,
                "message_a": None,
                "message_b": sb.get("message") if sb else None,
            })

    # Compare inputs
    inputs_a = run_a.get("inputs") or {}
    inputs_b = run_b.get("inputs") or {}
    inputs_diff: Dict[str, Dict[str, Any]] = {}
    for k in set(inputs_a.keys()) | set(inputs_b.keys()):
        val_a = inputs_a.get(k)
        val_b = inputs_b.get(k)
        if val_a != val_b:
            inputs_diff[k] = {"a": val_a, "b": val_b}

    # Compare final context keys
    ctx_a = run_a.get("context") or {}
    ctx_b = run_b.get("context") or {}
    context_diff: Dict[str, Dict[str, Any]] = {}
    for k in set(ctx_a.keys()) | set(ctx_b.keys()):
        val_a = ctx_a.get(k)
        val_b = ctx_b.get(k)
        if val_a != val_b:
            context_diff[k] = {"a": val_a, "b": val_b}

    return {
        "summary": {
            "workflow_name": run_b.get("workflow_name") or run_a.get("workflow_name"),
            "run_a_id": run_a.get("id"),
            "run_b_id": run_b.get("id"),
            "env_a": run_a.get("environment", "dev"),
            "env_b": run_b.get("environment", "dev"),
            "status_a": run_a.get("status"),
            "status_b": run_b.get("status"),
            "success_a": success_a,
            "success_b": success_b,
            "outcome": outcome,
            "time_a": time_a,
            "time_b": time_b,
            "time_delta": time_delta,
            "time_ratio": time_ratio,
            "regressed_steps_count": regressed_steps_count,
            "slower_steps_count": slower_steps_count,
            "inputs_differ_count": len(inputs_diff),
            "context_differ_count": len(context_diff),
        },
        "step_comparisons": step_comparisons,
        "inputs_diff": inputs_diff,
        "context_diff": context_diff,
        "run_a": run_a,
        "run_b": run_b,
    }
