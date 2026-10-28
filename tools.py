#!/usr/bin/env python3
"""Tool definitions for mcp-regression-watch."""

from mcp.types import Tool

TOOLS = [
    Tool(
        name="run_regression_check",
        description=(
            "Run a deploy-triggered regression check: behaviour-diffing against the persisted "
            "baseline, drift detection, breach flagging, and an overall pass/fail verdict. "
            "Persists the run (including raw run log — the two-column IP rule says raw run logs "
            "are customer-owned exit material)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "default": "mcp-agent-sla",
                    "description": "Service being checked (e.g. mcp-agent-sla).",
                },
                "version": {
                    "type": "string",
                    "default": "v2.1.0",
                    "description": "Version under test (e.g. v2.1.0).",
                },
                "seed": {
                    "type": "integer",
                    "description": "Optional seed for reproducible simulation.",
                },
                "persist": {
                    "type": "boolean",
                    "default": True,
                    "description": "Persist the run to state.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_drift_report",
        description=(
            "Aggregate the persisted run history into a drift report: drift trend per metric "
            "over time, count of breaches, worst-offending version, drift heat summary, and "
            "an alert list. All values computed from actual stored runs via Python statistics."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service to report on.",
                },
                "window_days": {
                    "type": "integer",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 365,
                    "description": "Look-back window in days.",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="get_comparison_report",
        description=(
            "Produce a retained comparison report between two versions: per-case side-by-side "
            "table (baseline value, candidate value, delta, pct drift, status), a diff summary "
            "(cases improved / regressed / unchanged / newly added / removed), a severity-ranked "
            "regression list, and the report's own content hash + generated timestamp. Must be "
            "retrievable / reproducible."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service to compare.",
                },
                "from_version": {
                    "type": "string",
                    "default": "v2.0.0",
                    "description": "Baseline version.",
                },
                "to_version": {
                    "type": "string",
                    "default": "v2.1.0",
                    "description": "Candidate version.",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="set_drift_threshold",
        description=(
            "Persist a per-metric drift threshold, validate the metric name against the known "
            "metric set and the threshold range, and record the threshold change with a "
            "timestamp so get_drift_report reflects it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "enum": [
                        "latency_p95_ms",
                        "tool_call_accuracy",
                        "hallucination_rate",
                        "json_schema_validity",
                        "token_cost",
                        "refusal_precision",
                        "retry_rate",
                        "throughput_rps",
                        "error_rate",
                    ],
                    "description": "Metric to set a threshold for.",
                },
                "threshold_pct": {
                    "type": "number",
                    "minimum": 0.1,
                    "maximum": 100.0,
                    "description": "Drift threshold as a percentage of baseline.",
                },
                "persist": {
                    "type": "boolean",
                    "default": True,
                    "description": "Persist the threshold to state.",
                },
            },
            "required": ["metric", "threshold_pct"],
        },
    ),
]