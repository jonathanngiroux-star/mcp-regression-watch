# mcp-regression-watch

MCP server for the **Agent Update Regression Watch** - deploy-triggered regression testing:
post-update behavior-diffing against baselines, drift alerts, retained regression-comparison
reports. Scheduled benchmarks catch planned drift; this catches the unplanned kind.

Pricing: $29-99/mo (rides the proofspan tier).

## Tools

### `run_regression_check`
Run a deploy-triggered regression check against the persisted baseline.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `service` | string | **required** | Service being checked (e.g. mcp-agent-sla) |
| `version` | string | **required** | Version under test (e.g. v2.1.0) |
| `seed` | integer | - | Optional seed for reproducible simulation |
| `persist` | boolean | `true` | Persist the run to state |

Returns per-case results with baseline value, current value, delta, pct drift, threshold, and status. Overall pass/fail plus breach list. Persists the raw run log (customer-owned exit material per two-column IP rule).

### `get_drift_report`
Aggregate persisted run history into a drift report.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `service` | string | **required** | Service to report on |
| `window_days` | integer | 30 | Look-back window in days (1-365) |

Returns drift trends per metric over time, breach counts, worst-offending version, drift heat summary, and alert list. All values computed from actual stored runs via Python statistics.

### `get_comparison_report`
Retained comparison report between two versions.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `service` | string | **required** | Service to compare |
| `from_version` | string | **required** | Baseline version |
| `to_version` | string | **required** | Candidate version |

Returns per-case side-by-side table, diff summary (improved/regressed/unchanged/added/removed), severity-ranked regression list, and content hash.

### `set_drift_threshold`
Persist a per-metric drift threshold.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `metric` | string enum | **required** | Metric (latency_p95_ms, tool_call_accuracy, hallucination_rate, json_schema_validity, token_cost, refusal_precision, retry_rate, throughput_rps, error_rate) |
| `threshold_pct` | number | **required** | Drift threshold as percentage of baseline (0.1-100.0) |
| `persist` | boolean | `true` | Persist to state |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

State persisted in `./state/regression_state.json`. Override with `MCP_REGRESSION_WATCH_STATE_DIR`.

## Connecting to an MCP client

```json
{
  "mcpServers": {
    "regression-watch": {
      "command": "python3",
      "args": ["/tmp/v3-services/mcp-regression-watch/main.py"]
    }
  }
}
```

## License

MIT