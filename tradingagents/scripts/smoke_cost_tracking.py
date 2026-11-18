#!/usr/bin/env python
"""Small real-token smoke test for Part 6 event capture.

This intentionally runs the existing graph with a tiny configuration and the
callback-based cost tracker.  It validates total token/latency capture only;
per-agent attribution waits for the Part 1 composition root to wrap nodes with
``with_agent_scope``.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from tradingagents.cost.agent_context import current_agent
from tradingagents.cost.budget import budget_for_profile
from tradingagents.cost.callback import CostTrackingCallback
from tradingagents.cost.monitor import CostMonitor
from tradingagents.cost.pricing import default_price_table
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smoke_cost_tracking.py")
    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--date", default="2026-11-14")
    parser.add_argument("--out", default="reports/part6/smoke.json")
    parser.add_argument("--max-tool-rounds", type=int, default=2)
    args = parser.parse_args(argv)

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(
        {
            "llm_provider": "deepseek",
            "quick_think_llm": "deepseek-flash",
            "deep_think_llm": "deepseek-flash",
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 1,
            "max_tool_rounds": args.max_tool_rounds,
            "max_tokens": 4096,
            "checkpoint_enabled": False,
            "output_language": "Chinese",
        }
    )

    run_id = f"smoke-{int(time.time())}"
    table = default_price_table()
    monitor = CostMonitor(table)
    callback = CostTrackingCallback(
        run_id=run_id,
        on_event=monitor.record,
        agent_name="unknown",
        provider="deepseek",
    )

    ta = TradingAgentsGraph(
        selected_analysts=("market",),
        debug=False,
        config=cfg,
        callbacks=[callback],
    )

    started = time.perf_counter()
    _, decision = ta.propagate(args.ticker, args.date)
    wall_seconds = time.perf_counter() - started

    budget = budget_for_profile("quick")
    report = monitor.report(run_id, budget, quality_floor_pass=True)
    payload = {
        "run_id": run_id,
        "ticker": args.ticker,
        "trade_date": args.date,
        "decision": str(decision),
        "wall_seconds": round(wall_seconds, 2),
        "event_count": len(monitor.events),
        "agent_context_at_end": current_agent(),
        "budget": budget.model_dump(mode="json"),
        "cost_report": report.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in monitor.events],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "run_id": run_id,
                "decision": str(decision),
                "wall_seconds": round(wall_seconds, 2),
                "event_count": len(monitor.events),
                "total_tokens": report.total_tokens,
                "estimated_cost_cny": str(report.cost),
                "over_budget": report.over_budget,
                "report": str(out),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
