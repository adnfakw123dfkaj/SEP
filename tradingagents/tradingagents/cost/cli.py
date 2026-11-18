"""Offline CLI entry points for Part 6 benchmark and token audit.

The scripts under ``scripts/`` are thin wrappers around these functions.  The
offline mode reads JSONL fixtures, so it works before Part 1-5 are available.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tradingagents.cost.audit import (
    TokenRun,
    assert_token_acceptance,
    build_token_report,
)
from tradingagents.cost.benchmark import (
    LatencySample,
    assert_latency_acceptance,
    latency_warnings,
    summarize_latency,
)
from tradingagents.cost.budget import budget_for_profile
from tradingagents.cost.pricing import default_price_table


def _load_jsonl(path: str | Path, model: type[BaseModel]) -> list[Any]:
    text = Path(path).read_text(encoding="utf-8")
    return [
        model.model_validate_json(line)
        for line in text.splitlines()
        if line.strip()
    ]


def _emit(payload: dict[str, Any], out: str | Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if out is None:
        print(text)
    else:
        Path(out).write_text(text + "\n", encoding="utf-8")


def bench_latency_main(argv: Sequence[str] | None = None) -> int:
    """Summarise latency samples and optionally apply acceptance gates."""
    parser = argparse.ArgumentParser(
        prog="bench_latency.py",
        description="Summarise latency samples from JSONL (offline mode).",
    )
    parser.add_argument("--profile", required=True, choices=["quick", "standard", "deep"])
    parser.add_argument("--samples-jsonl", required=True)
    parser.add_argument("--baseline-p95-s", type=float, default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--assert", dest="assert_gate", action="store_true")
    args = parser.parse_args(argv)

    samples: list[LatencySample] = _load_jsonl(args.samples_jsonl, LatencySample)
    report = summarize_latency(
        args.profile,
        samples,
        baseline_p95_s=args.baseline_p95_s,
    )

    payload = report.model_dump(mode="json")
    payload["gate_passed"] = None
    payload["warnings"] = latency_warnings(report)

    code = 0
    if args.assert_gate:
        try:
            payload["warnings"] = assert_latency_acceptance(report)
            payload["gate_passed"] = True
        except AssertionError as exc:
            payload["gate_passed"] = False
            payload["gate_error"] = str(exc)
            print(f"latency gate failed: {exc}", file=sys.stderr)
            code = 1

    _emit(payload, args.out)
    return code


def token_audit_main(argv: Sequence[str] | None = None) -> int:
    """Summarise token runs and optionally apply acceptance gates."""
    parser = argparse.ArgumentParser(
        prog="token_audit.py",
        description="Audit token/cost runs from JSONL (offline mode).",
    )
    parser.add_argument("--profile", required=True, choices=["quick", "standard", "deep"])
    parser.add_argument(
        "--runs-jsonl",
        "--events-jsonl",
        dest="runs_jsonl",
        required=True,
        help="TokenRun JSONL; --events-jsonl is accepted as an alias.",
    )
    parser.add_argument("--hard-limit", type=int, default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--assert", dest="assert_gate", action="store_true")
    args = parser.parse_args(argv)

    runs: list[TokenRun] = _load_jsonl(args.runs_jsonl, TokenRun)
    table = default_price_table()
    report = build_token_report(args.profile, runs, table)
    hard_limit = (
        args.hard_limit
        if args.hard_limit is not None
        else budget_for_profile(args.profile).hard_limit
    )

    payload = report.model_dump(mode="json")
    payload["hard_limit"] = hard_limit
    payload["gate_passed"] = None

    code = 0
    if args.assert_gate:
        try:
            assert_token_acceptance(report, hard_limit=hard_limit)
            payload["gate_passed"] = True
        except AssertionError as exc:
            payload["gate_passed"] = False
            payload["gate_error"] = str(exc)
            print(f"token audit gate failed: {exc}", file=sys.stderr)
            code = 1

    _emit(payload, args.out)
    return code


__all__ = ["bench_latency_main", "token_audit_main"]
