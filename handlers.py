#!/usr/bin/env python3
"""Real business logic for mcp-regression-watch handlers."""

import hashlib
import json
import os
import random
import statistics
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------

def _state_dir() -> Path:
    override = os.environ.get("MCP_REGRESSION_WATCH_STATE_DIR")
    path = Path(override) if override else Path(__file__).resolve().parent / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path() -> Path:
    return _state_dir() / "regression_state.json"


def _default_state() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "runs": [],
        "baselines": {},
        "thresholds": {
            "latency_p95_ms": 10.0,
            "tool_call_accuracy": 5.0,
            "hallucination_rate": 2.0,
            "json_schema_validity": 1.0,
            "token_cost": 15.0,
            "refusal_precision": 3.0,
            "retry_rate": 10.0,
            "throughput_rps": 10.0,
            "error_rate": 5.0,
        },
        "sequence": 0,
    }


def load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        state = _default_state()
        save_state(state)
        return state
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        state = _default_state()
    base = _default_state()
    base.update(state)
    for key, default in _default_state().items():
        if key not in base:
            base[key] = default
    return state


def save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".regression-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# --------------------------------------------------------------------------
# Domain data
# --------------------------------------------------------------------------

SEED_BASELINE = {
    "service": "mcp-regression-watch",
    "version": "v2.0.0",
    "established_at": "2026-08-01T00:00:00Z",
    "cases": {
        "case-001": {"metric": "latency_p95_ms", "value": 245.3, "unit": "ms"},
        "case-002": {"metric": "tool_call_accuracy", "value": 98.7, "unit": "%"},
        "case-003": {"metric": "hallucination_rate", "value": 0.8, "unit": "%"},
        "case-004": {"metric": "json_schema_validity", "value": 99.9, "unit": "%"},
        "case-005": {"metric": "token_cost", "value": 0.0124, "unit": "USD/k"},
        "case-006": {"metric": "refusal_precision", "value": 96.2, "unit": "%"},
        "case-007": {"metric": "retry_rate", "value": 2.1, "unit": "%"},
        "case-008": {"metric": "throughput_rps", "value": 42.5, "unit": "rps"},
        "case-009": {"metric": "error_rate", "value": 0.3, "unit": "%"},
        "case-010": {"metric": "latency_p50_ms", "value": 87.1, "unit": "ms"},
        "case-011": {"metric": "latency_p99_ms", "value": 612.8, "unit": "ms"},
        "case-012": {"metric": "token_throughput", "value": 3400, "unit": "tok/s"},
    },
}

METRICS = [
    "latency_p95_ms",
    "tool_call_accuracy",
    "hallucination_rate",
    "json_schema_validity",
    "token_cost",
    "refusal_precision",
    "retry_rate",
    "throughput_rps",
    "error_rate",
]

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _content_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def _baseline_key(service: str, version: str) -> str:
    return f"{service}@{version}"


def _get_baseline(state: dict[str, Any], service: str, version: str) -> dict[str, Any] | None:
    key = _baseline_key(service, version)
    return state.get("baselines", {}).get(key)


def _set_baseline(state: dict[str, Any], service: str, version: str, baseline: dict[str, Any]) -> None:
    key = _baseline_key(service, version)
    state.setdefault("baselines", {})[key] = baseline


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------

def _handler_run_regression_check(arguments: dict) -> dict[str, Any]:
    service = str(arguments.get("service", "mcp-agent-sla")).strip()
    version = str(arguments.get("version", "v2.1.0")).strip()
    seed = arguments.get("seed")
    persist = bool(arguments.get("persist", True))

    state = load_state()

    # Get or establish baseline
    baseline = _get_baseline(state, service, version)
    if baseline is None:
        # Establish baseline from the seeded one, but use the given version
        baseline = {
            "service": service,
            "version": version,
            "established_at": _fmt(_now()),
            "cases": {k: dict(v) for k, v in SEED_BASELINE["cases"].items()},
        }
        _set_baseline(state, service, version, baseline)

    # Also ensure a v2.0.0 baseline exists for comparison reports
    baseline_v20 = _get_baseline(state, service, "v2.0.0")
    if baseline_v20 is None:
        baseline_v20 = {
            "service": service,
            "version": "v2.0.0",
            "established_at": _fmt(_now() - timedelta(days=30)),
            "cases": {k: dict(v) for k, v in SEED_BASELINE["cases"].items()},
        }
        _set_baseline(state, service, "v2.0.0", baseline_v20)

    # Simulate current run against baseline
    rng = random.Random(seed if seed is not None else int(_now().timestamp() * 1000) % 2**32)

    run_id = f"run-{hashlib.sha256(f'{service}|{version}|{_now().isoformat()}'.encode()).hexdigest()[:10]}"
    results: dict[str, Any] = {"cases": {}, "overall": "pass", "breaches": []}

    for case_id, case_def in baseline["cases"].items():
        metric = case_def["metric"]
        baseline_value = case_def["value"]
        # Simulate: current value varies around baseline with some drift
        drift_factor = rng.uniform(-0.05, 0.08)  # slight positive drift bias
        if metric == "hallucination_rate":
            drift_factor = rng.uniform(-0.02, 0.12)  # can drift more
        elif metric == "error_rate":
            drift_factor = rng.uniform(-0.1, 0.15)

        current_value = round(baseline_value * (1 + drift_factor), 4)
        delta = round(current_value - baseline_value, 4)
        pct_drift = round((delta / baseline_value * 100) if baseline_value != 0 else 0.0, 2)

        threshold = state.get("thresholds", {}).get(metric, 10.0)
        breached = abs(pct_drift) > threshold
        status = "fail" if breached else "pass"

        results["cases"][case_id] = {
            "metric": metric,
            "unit": case_def["unit"],
            "baseline_value": baseline_value,
            "current_value": current_value,
            "delta": delta,
            "pct_drift": pct_drift,
            "threshold_pct": threshold,
            "status": status,
        }
        if breached:
            results["overall"] = "fail"
            results["breaches"].append(
                {
                    "case_id": case_id,
                    "metric": metric,
                    "pct_drift": pct_drift,
                    "threshold_pct": threshold,
                }
            )

    run_record = {
        "run_id": run_id,
        "service": service,
        "version": version,
        "seed": seed,
        "started_at": _fmt(_now()),
        "finished_at": _fmt(_now() + timedelta(seconds=1)),
        "baseline_version": baseline.get("version"),
        "overall": results["overall"],
        "breaches": results["breaches"],
        "cases": results["cases"],
        "raw_log": f"Regression run {run_id} for {service}@{version}; seed={seed}",
    }

    if persist:
        state.setdefault("runs", []).insert(0, run_record)
        state["sequence"] = state.get("sequence", 0) + 1
        save_state(state)

    return results


def _handler_get_drift_report(arguments: dict) -> dict[str, Any]:
    service = str(arguments.get("service", "")).strip()
    if not service:
        return {"status": "error", "error": "service is required"}
    window_days = int(arguments.get("window_days", 30))
    if window_days < 1 or window_days > 365:
        return {"status": "error", "error": "window_days must be 1-365"}

    state = load_state()
    cutoff = _now() - timedelta(days=window_days)
    runs = [r for r in state.get("runs", []) if r.get("service") == service and _parse_ts(r["started_at"]) >= cutoff]
    if not runs and window_days >= 365:
        runs = [r for r in state.get("runs", []) if r.get("service") == service]

    drift_trends: dict[str, list[float]] = {}
    breach_counts: dict[str, int] = {}
    for run in runs:
        for breach in run.get("breaches", []):
            metric = breach["metric"]
            drift_trends.setdefault(metric, []).append(breach["pct_drift"])
            breach_counts[metric] = breach_counts.get(metric, 0) + 1

    worst: dict[str, Any] | None = None
    for run in runs:
        for breach in run.get("breaches", []):
            if worst is None or abs(breach["pct_drift"]) > abs(worst["pct_drift"]):
                worst = {
                    "run_id": run["run_id"],
                    "version": run["version"],
                    "metric": breach["metric"],
                    "pct_drift": breach["pct_drift"],
                    "threshold_pct": breach["threshold_pct"],
                }

    alert_list = []
    for run in runs[:20]:
        if run["overall"] == "fail":
            alert_list.append(
                {
                    "run_id": run["run_id"],
                    "version": run["version"],
                    "started_at": run["started_at"],
                    "breach_count": len(run["breaches"]),
                    "worst_metric": max(run["breaches"], key=lambda b: abs(b["pct_drift"]))["metric"],
                }
            )

    trend_summary = {}
    for metric, values in drift_trends.items():
        if len(values) >= 2:
            trend = "increasing" if values[0] > values[-1] else "decreasing"
            trend_summary[metric] = {
                "samples": len(values),
                "latest": values[0],
                "oldest": values[-1],
                "mean_abs_drift": round(statistics.mean(abs(v) for v in values), 2),
                "trend": trend,
            }
        elif values:
            trend_summary[metric] = {
                "samples": 1,
                "latest": values[0],
                "mean_abs_drift": round(abs(values[0]), 2),
            }

    return {
        "service": service,
        "window_days": window_days,
        "runs_analyzed": len(runs),
        "total_breaches": sum(breach_counts.values()),
        "breaches_by_metric": breach_counts,
        "worst_offender": worst,
        "drift_trends": trend_summary,
        "alert_list": alert_list,
        "thresholds_in_effect": state.get("thresholds", {}),
    }


def _handler_get_comparison_report(arguments: dict) -> dict[str, Any]:
    service = str(arguments.get("service", "mcp-agent-sla")).strip()
    from_version = str(arguments.get("from_version", "v2.0.0")).strip()
    to_version = str(arguments.get("to_version", "v2.1.0")).strip()
    if not service:
        return {"status": "error", "error": "service is required"}

    state = load_state()
    baseline = _get_baseline(state, service, from_version)
    candidate_run = None
    for run in state.get("runs", []):
        if run.get("service") == service and run.get("version") == to_version:
            candidate_run = run
            break

    if baseline is None:
        return {"status": "error", "error": f"no baseline for {service}@{from_version}"}
    if candidate_run is None:
        return {"status": "error", "error": f"no run found for {service}@{to_version}"}

    candidate_cases = candidate_run.get("cases", {})

    side_by_side = []
    improved = regressed = unchanged = added = removed = 0
    regression_list = []

    baseline_cases = baseline.get("cases", {})
    all_ids = set(baseline_cases.keys()) | set(candidate_cases.keys())

    for case_id in sorted(all_ids):
        b = baseline_cases.get(case_id)
        c = candidate_cases.get(case_id)
        if b is None:
            status = "added"
            added += 1
            row = {"case_id": case_id, "status": status, "note": "New case in candidate"}
        elif c is None:
            status = "removed"
            removed += 1
            row = {"case_id": case_id, "status": status, "note": "Case removed in candidate"}
        else:
            delta = round(c["current_value"] - b["value"], 4)
            pct_drift = round((delta / b["value"] * 100) if b["value"] != 0 else 0.0, 2)
            threshold = c.get("threshold_pct", state.get("thresholds", {}).get(b["metric"], 10.0))
            status = "regressed" if abs(pct_drift) > threshold else ("improved" if delta < 0 and b["metric"] in ("latency_p95_ms", "token_cost", "error_rate", "retry_rate") else "unchanged")
            if status == "regressed":
                regressed += 1
                regression_list.append(
                    {
                        "case_id": case_id,
                        "metric": b["metric"],
                        "pct_drift": pct_drift,
                        "threshold_pct": threshold,
                        "severity": "high" if abs(pct_drift) > threshold * 2 else "medium",
                    }
                )
            elif status == "improved":
                improved += 1
            else:
                unchanged += 1
            row = {
                "case_id": case_id,
                "metric": b["metric"],
                "unit": b["unit"],
                "baseline_value": b["value"],
                "candidate_value": c["current_value"],
                "delta": delta,
                "pct_drift": pct_drift,
                "threshold_pct": threshold,
                "status": status,
            }
        side_by_side.append(row)

    regression_list.sort(key=lambda r: abs(r["pct_drift"]), reverse=True)

    report = {
        "service": service,
        "from_version": from_version,
        "to_version": to_version,
        "generated_at": _fmt(_now()),
        "side_by_side": side_by_side,
        "diff_summary": {
            "improved": improved,
            "regressed": regressed,
            "unchanged": unchanged,
            "added": added,
            "removed": removed,
            "total_compared": len(side_by_side),
        },
        "regression_list": regression_list,
        "content_hash": _content_hash(
            {"side_by_side": side_by_side, "diff_summary": {"improved": improved, "regressed": regressed}}
        ),
    }
    return report


def _handler_set_drift_threshold(arguments: dict) -> dict[str, Any]:
    metric = str(arguments.get("metric", "")).strip()
    threshold_pct = float(arguments.get("threshold_pct", 0))
    persist = bool(arguments.get("persist", True))

    if metric not in METRICS:
        return {
            "status": "error",
            "error": f"unknown metric {metric!r}",
            "valid_metrics": METRICS,
        }
    if threshold_pct < 0.1 or threshold_pct > 100.0:
        return {"status": "error", "error": "threshold_pct must be between 0.1 and 100.0"}

    state = load_state()
    old = state.get("thresholds", {}).get(metric)
    state.setdefault("thresholds", {})[metric] = threshold_pct
    state.setdefault("threshold_history", []).insert(
        0,
        {
            "metric": metric,
            "old_threshold": old,
            "new_threshold": threshold_pct,
            "changed_at": _fmt(_now()),
        },
    )
    if persist:
        save_state(state)

    return {
        "metric": metric,
        "old_threshold_pct": old,
        "new_threshold_pct": threshold_pct,
        "persisted": persist,
        "history_entry": state["threshold_history"][0] if persist else None,
    }


HANDLERS = {
    "run_regression_check": _handler_run_regression_check,
    "get_drift_report": _handler_get_drift_report,
    "get_comparison_report": _handler_get_comparison_report,
    "set_drift_threshold": _handler_set_drift_threshold,
}