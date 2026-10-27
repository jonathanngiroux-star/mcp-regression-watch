# mcp-regression-watch

MCP server for Agent Update Regression Watch - run regression checks, get drift reports, compare versions.

## Tools

### run_regression_check
Run regression check on agent after update.

**Parameters:**
- `agent_id` (string, required): Agent identifier
- `from_version` (string, required): Previous version
- `to_version` (string, required): New version
- `test_suite` (string, optional): "full", "quick", or "critical_only" (default: "full")

### get_drift_report
Get drift report for an agent over time.

**Parameters:**
- `agent_id` (string, required): Agent identifier
- `days` (integer, optional): Days of history (default: 30)

### get_comparison_report
Get detailed comparison report between versions.

**Parameters:**
- `agent_id` (string, required): Agent identifier
- `from_version` (string, required): Previous version
- `to_version` (string, required): New version

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Connecting to Claude Desktop

```json
{
  "mcpServers": {
    "regression-watch": {
      "command": "python",
      "args": ["/path/to/mcp-regression-watch/main.py"],
      "cwd": "/path/to/mcp-regression-watch"
    }
  }
}
```

## License

MIT