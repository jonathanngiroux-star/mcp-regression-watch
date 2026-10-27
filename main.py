#!/usr/bin/env python3
"""MCP server for regression-watch - Agent Update Regression Watch"""

import json
import os
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("mcp-regression-watch")

AGENTS = {
    "agent-001": {
        "id": "agent-001",
        "name": "Trading Bot Alpha",
        "current_version": "v2.3.1",
        "previous_version": "v2.2.0",
        "last_update": "2024-12-20T10:00:00",
        "baseline_metrics": {"latency_p50_ms": 45, "latency_p99_ms": 120, "error_rate": 0.001, "throughput_tps": 150},
        "current_metrics": {"latency_p50_ms": 42, "latency_p99_ms": 115, "error_rate": 0.0008, "throughput_tps": 155},
        "regression_detected": False
    },
    "agent-002": {
        "id": "agent-002",
        "name": "Monitoring Agent",
        "current_version": "v1.1.0",
        "previous_version": "v1.0.5",
        "last_update": "2024-12-15T10:00:00",
        "baseline_metrics": {"latency_p50_ms": 30, "latency_p99_ms": 80, "error_rate": 0.002, "memory_mb": 256},
        "current_metrics": {"latency_p50_ms": 35, "latency_p99_ms": 95, "error_rate": 0.005, "memory_mb": 380},
        "regression_detected": True
    }
}

REGRESSION_CHECKS = {
    "check-001": {
        "id": "check-001",
        "agent_id": "agent-001",
        "trigger": "version_update",
        "from_version": "v2.2.0",
        "to_version": "v2.3.1",
        "status": "passed",
        "started_at": "2024-12-20T10:05:00",
        "completed_at": "2024-12-20T10:35:00",
        "drift_detected": False,
        "details": {"metrics_compared": 8, "regressions": 0, "improvements": 3}
    },
    "check-002": {
        "id": "check-002",
        "agent_id": "agent-002",
        "trigger": "version_update",
        "from_version": "v1.0.5",
        "to_version": "v1.1.0",
        "status": "failed",
        "started_at": "2024-12-15T10:05:00",
        "completed_at": "2024-12-15T10:30:00",
        "drift_detected": True,
        "details": {"metrics_compared": 6, "regressions": 2, "improvements": 1}
    }
}

COMPARISON_REPORTS = {
    "comp-001": {
        "id": "comp-001",
        "agent_id": "agent-001",
        "from_version": "v2.2.0",
        "to_version": "v2.3.1",
        "generated_at": "2024-12-20T10:35:00",
        "metric_diffs": {
            "latency_p50_ms": {"before": 45, "after": 42, "change_pct": -6.7, "status": "improved"},
            "latency_p99_ms": {"before": 120, "after": 115, "change_pct": -4.2, "status": "improved"},
            "error_rate": {"before": 0.001, "after": 0.0008, "change_pct": -20.0, "status": "improved"},
            "throughput_tps": {"before": 150, "after": 155, "change_pct": 3.3, "status": "improved"}
        },
        "overall_status": "passed",
        "recommendations": []
    },
    "comp-002": {
        "id": "comp-002",
        "agent_id": "agent-002",
        "from_version": "v1.0.5",
        "to_version": "v1.1.0",
        "generated_at": "2024-12-15T10:30:00",
        "metric_diffs": {
            "latency_p50_ms": {"before": 30, "after": 35, "change_pct": 16.7, "status": "regressed"},
            "latency_p99_ms": {"before": 80, "after": 95, "change_pct": 18.8, "status": "regressed"},
            "error_rate": {"before": 0.002, "after": 0.005, "change_pct": 150.0, "status": "regressed"},
            "memory_mb": {"before": 256, "after": 380, "change_pct": 48.4, "status": "regressed"}
        },
        "overall_status": "failed",
        "recommendations": [
            "Rollback to v1.0.5 immediately",
            "Investigate memory leak in metrics collector",
            "Review error handling in new health check module"
        ]
    }
}

app = Server("mcp-regression-watch")

TOOLS = [
    Tool(
        name="run_regression_check",
        description="Run regression check on agent after update",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent identifier"},
                "from_version": {"type": "string", "description": "Previous version"},
                "to_version": {"type": "string", "description": "New version"},
                "test_suite": {"type": "string", "enum": ["full", "quick", "critical_only"], "default": "full", "description": "Test suite to run"}
            },
            "required": ["agent_id", "from_version", "to_version"]
        }
    ),
    Tool(
        name="get_drift_report",
        description="Get drift report for an agent",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent identifier"},
                "days": {"type": "integer", "default": 30, "description": "Days of history"}
            },
            "required": ["agent_id"]
        }
    ),
    Tool(
        name="get_comparison_report",
        description="Get detailed comparison report between versions",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent identifier"},
                "from_version": {"type": "string", "description": "Previous version"},
                "to_version": {"type": "string", "description": "New version"}
            },
            "required": ["agent_id", "from_version", "to_version"]
        }
    )
]

@app.list_tools()
async def list_tools():
    return TOOLS

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "run_regression_check":
        agent_id = arguments.get("agent_id")
        from_version = arguments.get("from_version")
        to_version = arguments.get("to_version")
        test_suite = arguments.get("test_suite", "full")
        
        if agent_id not in AGENTS:
            return [TextContent(type="text", text=json.dumps({"error": f"Agent not found: {agent_id}"}))]
        
        agent = AGENTS[agent_id]
        
        # Simulate regression check
        check_id = f"check-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Compare metrics
        baseline = agent["baseline_metrics"]
        current = agent["current_metrics"]
        
        regressions = 0
        improvements = 0
        metric_diffs = {}
        
        for key in baseline:
            if key in current:
                before = baseline[key]
                after = current[key]
                if before != 0:
                    change_pct = ((after - before) / before) * 100
                else:
                    change_pct = 0
                
                # Determine if regression (higher latency/error/memory is bad, lower throughput is bad)
                is_regression = False
                is_improvement = False
                if key in ["latency_p50_ms", "latency_p99_ms", "error_rate", "memory_mb"]:
                    if change_pct > 10:  # >10% increase is regression
                        is_regression = True
                        regressions += 1
                    elif change_pct < -5:  # >5% decrease is improvement
                        is_improvement = True
                        improvements += 1
                elif key in ["throughput_tps"]:
                    if change_pct < -10:  # >10% decrease is regression
                        is_regression = True
                        regressions += 1
                    elif change_pct > 5:  # >5% increase is improvement
                        is_improvement = True
                        improvements += 1
                
                status = "regressed" if is_regression else "improved" if is_improvement else "stable"
                metric_diffs[key] = {"before": before, "after": after, "change_pct": round(change_pct, 1), "status": status}
        
        overall_status = "failed" if regressions > 0 else "passed"
        
        check_result = {
            "id": check_id,
            "agent_id": agent_id,
            "trigger": "version_update",
            "from_version": from_version,
            "to_version": to_version,
            "status": overall_status,
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "drift_detected": regressions > 0,
            "details": {"metrics_compared": len(metric_diffs), "regressions": regressions, "improvements": improvements}
        }
        
        REGRESSION_CHECKS[check_id] = check_result
        
        # Update agent
        agent["current_version"] = to_version
        agent["previous_version"] = from_version
        agent["last_update"] = datetime.now().isoformat()
        agent["regression_detected"] = regressions > 0
        
        # Create comparison report
        comp_id = f"comp-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        COMPARISON_REPORTS[comp_id] = {
            "id": comp_id,
            "agent_id": agent_id,
            "from_version": from_version,
            "to_version": to_version,
            "generated_at": datetime.now().isoformat(),
            "metric_diffs": metric_diffs,
            "overall_status": overall_status,
            "recommendations": [
                f"Rollback to {from_version} immediately",
                "Investigate root cause of regressions"
            ] if regressions > 0 else []
        }
        
        result = {"status": "ok", "tool": "run_regression_check", "check": check_result, "comparison_report_id": comp_id}
        return [TextContent(type="text", text=json.dumps(result))]
    
    elif name == "get_drift_report":
        agent_id = arguments.get("agent_id")
        days = arguments.get("days", 30)
        
        if agent_id not in AGENTS:
            return [TextContent(type="text", text=json.dumps({"error": f"Agent not found: {agent_id}"}))]
        
        agent = AGENTS[agent_id]
        checks = [c for c in REGRESSION_CHECKS.values() if c["agent_id"] == agent_id]
        
        # Simulate daily drift data
        import random
        drift_history = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            drift_history.append({
                "date": date,
                "drift_score": round(random.uniform(0, 0.3), 3),
                "metric_count": len(agent["baseline_metrics"]),
                "alerts": random.randint(0, 2)
            })
        
        result = {
            "status": "ok",
            "tool": "get_drift_report",
            "agent_id": agent_id,
            "agent_name": agent["name"],
            "current_version": agent["current_version"],
            "regression_detected": agent["regression_detected"],
            "drift_history": drift_history,
            "recent_checks": checks[-5:],
            "summary": {
                "total_checks": len(checks),
                "passed": len([c for c in checks if c["status"] == "passed"]),
                "failed": len([c for c in checks if c["status"] == "failed"]),
                "avg_drift_score": round(sum(d["drift_score"] for d in drift_history) / len(drift_history), 3)
            }
        }
        return [TextContent(type="text", text=json.dumps(result))]
    
    elif name == "get_comparison_report":
        agent_id = arguments.get("agent_id")
        from_version = arguments.get("from_version")
        to_version = arguments.get("to_version")
        
        # Find matching comparison report
        report = None
        for r in COMPARISON_REPORTS.values():
            if r["agent_id"] == agent_id and r["from_version"] == from_version and r["to_version"] == to_version:
                report = r
                break
        
        if not report:
            return [TextContent(type="text", text=json.dumps({"error": f"Comparison report not found for {agent_id} {from_version} -> {to_version}"}))]
        
        result = {"status": "ok", "tool": "get_comparison_report", "report": report}
        return [TextContent(type="text", text=json.dumps(result))]
    
    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    from datetime import timedelta
    
    async def serve():
        reader, writer = await stdio_server()
        await app.run(reader, writer)
    
    asyncio.run(serve())