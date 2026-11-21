"""CLI entry points for Part 6 benchmarks and token audits.

Both commands support an offline JSONL mode and a live mode. Live mode runs the
real graph with the selected profile and a temporary cache/results tree so cold
and warm measurements are repeatable without touching the user's run data.
Artifacts are removed by default; `--keep-artifacts` retains a generated tree,
while `--workdir` writes into an explicit empty directory for inspection.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tradingagents.contracts.llm_event import RoutePath
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


def _baseline_p95(args) -> float | None:
    if args.baseline_p95_s is not None:
        return args.baseline_p95_s
    if args.baseline:
        data = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        for key in ("baseline_p95_s", "p95_s", "p95"):
            if data.get(key) is not None:
                return float(data[key])
    return None


@contextmanager
def _live_workspace(
    workdir: str | Path | None,
    keep_artifacts: bool,
) -> Iterator[tuple[Path, bool]]:
    """Yield a live workspace root and whether it survives the run."""
    if workdir is not None:
        root = Path(workdir).expanduser().resolve()
        if root.exists() and not root.is_dir():
            raise ValueError(f"live workdir is not a directory: {root}")
        if root.exists() and any(root.iterdir()):
            raise ValueError(f"live workdir must be empty: {root}")
        root.mkdir(parents=True, exist_ok=True)
        yield root, True
        return

    if keep_artifacts:
        yield Path(tempfile.mkdtemp(prefix="ta-part6-live-")), True
        return

    with tempfile.TemporaryDirectory(prefix="ta-part6-live-") as temp_root:
        yield Path(temp_root), False


def _run_live(
    profile: str,
    ticker: str,
    trade_date: str | None,
    cold: int,
    warm: int,
    *,
    workdir: str | Path | None = None,
    keep_artifacts: bool = False,
) -> tuple[list[LatencySample], list[TokenRun], Path | None]:
    """Run the real graph and return samples, runs, and retained artifacts."""
    from tradingagents.dataflows.date_window import get_current_date
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.profiles import build_profile, profile_to_runtime_config

    trade_date = trade_date or get_current_date()
    samples: list[LatencySample] = []
    runs: list[TokenRun] = []
    retained: Path | None = None

    with _live_workspace(workdir, keep_artifacts) as (root, kept):
        if kept:
            retained = root
        config = profile_to_runtime_config(build_profile(profile), DEFAULT_CONFIG.copy())
        config.update(
            results_dir=str(root / "results"),
            data_cache_dir=str(root / "cache"),
            memory_log_path=str(root / "memory.md"),
            checkpoint_enabled=False,
        )
        graph = TradingAgentsGraph(config=config)

        def run_one(cache_state: str) -> None:
            cache_dir = Path(config["data_cache_dir"])
            if cache_state == "cold":
                shutil.rmtree(cache_dir, ignore_errors=True)
            started = time.perf_counter()
            state: dict[str, Any] = {}
            error: Exception | None = None
            try:
                state, _ = graph.propagate(ticker, trade_date)
            except Exception as exc:  # a failed sample still counts toward the rate
                error = exc
            duration = time.perf_counter() - started
            samples.append(
                LatencySample(
                    profile=profile,
                    cache_state=cache_state,
                    duration_s=duration,
                    success=error is None,
                )
            )

            report = state.get("cost_report") or {}
            route_paths = []
            for path in report.get("route_paths", []):
                try:
                    route_paths.append(RoutePath(path))
                except ValueError:
                    route_paths.append(RoutePath.DIRECT)
            cost = Decimal(str(state.get("cost_estimate") or 0))
            runs.append(
                TokenRun(
                    run_id=f"{ticker}-{trade_date}-{len(runs)}",
                    profile=profile,
                    total_tokens=int(report.get("total_tokens", 0)),
                    has_report=bool(report),
                    silent_over_budget=bool(
                        report.get("over_budget")
                        and not state.get("budget_exceeded")
                    ),
                    cost=cost,
                    cost_ground_truth=cost,
                    quality_floor_pass=bool(
                        state.get("output_validation", {}).get("ok", True)
                    ),
                    route_paths=route_paths or [RoutePath.DIRECT],
                )
            )

        for _ in range(cold):
            run_one("cold")
        if warm and not cold:
            # Populate the cache with one unmeasured run before warm samples.
            run_one("warm")
            samples.clear()
            runs.clear()
        for _ in range(warm):
            run_one("warm")

    return samples, runs, retained


def _latency_gate_failures(report, args) -> list[str]:
    failures: list[str] = []
    if args.assert_p95 is not None and report.p95_s > args.assert_p95:
        failures.append(f"p95 {report.p95_s:.1f}s > {args.assert_p95:.1f}s")
    if args.assert_p99_ratio is not None:
        ratio = report.p99_s / report.p95_s if report.p95_s else 0.0
        if ratio > args.assert_p99_ratio:
            failures.append(f"p99/p95 {ratio:.3f} > {args.assert_p99_ratio:.3f}")
    if args.assert_failure_rate is not None and report.failure_rate > args.assert_failure_rate:
        failures.append(
            f"failure rate {report.failure_rate:.3f} > {args.assert_failure_rate:.3f}"
        )
    if (
        args.assert_improvement is not None
        and (report.improvement is None or report.improvement < args.assert_improvement)
    ):
        failures.append(
            f"improvement {report.improvement!r} < {args.assert_improvement:.3f}"
        )
    return failures


def bench_latency_main(argv: Sequence[str] | None = None) -> int:
    """Measure or summarise latency; live mode runs when no JSONL is supplied."""
    parser = argparse.ArgumentParser(
        prog="bench_latency.py",
        description="Measure latency with the real graph or summarise JSONL samples.",
    )
    parser.add_argument("--profile", required=True, choices=["quick", "standard", "deep"])
    parser.add_argument("--samples-jsonl", default=None)
    parser.add_argument("--cold", type=int, default=None)
    parser.add_argument("--warm", type=int, default=None)
    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--date", default=None)
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--baseline-p95-s", type=float, default=None)
    parser.add_argument("--assert-p95", type=float, default=None)
    parser.add_argument("--assert-p99-ratio", type=float, default=None)
    parser.add_argument("--assert-failure-rate", type=float, default=None)
    parser.add_argument("--assert-improvement", type=float, default=None)
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--keep-artifacts", action="store_true")
    parser.add_argument("--out", default=None)
    parser.add_argument("--assert", dest="assert_gate", action="store_true")
    args = parser.parse_args(argv)

    retained: Path | None = None
    if args.samples_jsonl:
        samples: list[LatencySample] = _load_jsonl(args.samples_jsonl, LatencySample)
    else:
        default_runs = 3 if args.profile == "deep" else 15
        cold = args.cold if args.cold is not None else default_runs
        warm = args.warm if args.warm is not None else default_runs
        if cold + warm == 0:
            parser.error("live mode needs --cold or --warm samples")
        try:
            samples, _, retained = _run_live(
                args.profile,
                args.ticker,
                args.date,
                cold,
                warm,
                workdir=args.workdir,
                keep_artifacts=args.keep_artifacts,
            )
        except Exception as exc:
            print(f"live latency benchmark could not start: {exc}", file=sys.stderr)
            return 2

    report = summarize_latency(
        args.profile,
        samples,
        baseline_p95_s=_baseline_p95(args),
    )
    payload = report.model_dump(mode="json")
    payload["mode"] = "live" if not args.samples_jsonl else "jsonl"
    payload["artifacts_kept"] = retained is not None
    if retained is not None:
        payload["artifacts_dir"] = str(retained)
    payload["gate_passed"] = None
    payload["warnings"] = latency_warnings(report)

    failures = _latency_gate_failures(report, args)
    code = 0
    if args.assert_gate:
        try:
            payload["warnings"] = assert_latency_acceptance(report)
        except AssertionError as exc:
            failures.append(str(exc))
    if failures:
        payload["gate_passed"] = False
        payload["gate_error"] = "; ".join(failures)
        print(f"latency gate failed: {payload['gate_error']}", file=sys.stderr)
        code = 1
    elif args.assert_gate or any(
        value is not None
        for value in (
            args.assert_p95,
            args.assert_p99_ratio,
            args.assert_failure_rate,
            args.assert_improvement,
        )
    ):
        payload["gate_passed"] = True
    _emit(payload, args.out)
    return code


def _token_gate_failures(report, args) -> list[str]:
    failures: list[str] = []
    if args.assert_p95 is not None and report.p95_tokens > args.assert_p95:
        failures.append(f"p95 tokens {report.p95_tokens} > {args.assert_p95}")
    if (
        args.assert_report_coverage is not None
        and report.report_coverage != args.assert_report_coverage
    ):
        failures.append(
            f"report coverage {report.report_coverage:.3f} "
            f"!= {args.assert_report_coverage:.3f}"
        )
    if (
        args.assert_silent_over_budget is not None
        and report.silent_over_budget_runs != args.assert_silent_over_budget
    ):
        failures.append(
            f"silent over-budget runs {report.silent_over_budget_runs} "
            f"!= {args.assert_silent_over_budget}"
        )
    if (
        args.assert_cost_error is not None
        and report.cost_relative_error > args.assert_cost_error
    ):
        failures.append(
            f"cost error {report.cost_relative_error:.3f} "
            f"> {args.assert_cost_error:.3f}"
        )
    if (
        args.assert_routed_quality is not None
        and report.routed_quality_floor_pass_rate != args.assert_routed_quality
    ):
        failures.append(
            f"routed quality {report.routed_quality_floor_pass_rate:.3f} "
            f"!= {args.assert_routed_quality:.3f}"
        )
    return failures


def token_audit_main(argv: Sequence[str] | None = None) -> int:
    """Measure or audit token/cost; live mode runs when no JSONL is supplied."""
    parser = argparse.ArgumentParser(
        prog="token_audit.py",
        description="Audit token/cost with the real graph or a JSONL fixture.",
    )
    parser.add_argument("--profile", required=True, choices=["quick", "standard", "deep"])
    parser.add_argument(
        "--runs-jsonl",
        "--events-jsonl",
        dest="runs_jsonl",
        default=None,
        help="TokenRun JSONL; --events-jsonl is accepted as an alias.",
    )
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--date", default=None)
    parser.add_argument("--hard-limit", type=int, default=None)
    parser.add_argument("--assert-p95", type=int, default=None)
    parser.add_argument("--assert-report-coverage", type=float, default=None)
    parser.add_argument("--assert-silent-over-budget", type=int, default=None)
    parser.add_argument("--assert-cost-error", type=float, default=None)
    parser.add_argument("--assert-routed-quality", type=float, default=None)
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--keep-artifacts", action="store_true")
    parser.add_argument("--out", default=None)
    parser.add_argument("--assert", dest="assert_gate", action="store_true")
    args = parser.parse_args(argv)

    retained: Path | None = None
    if args.runs_jsonl:
        runs: list[TokenRun] = _load_jsonl(args.runs_jsonl, TokenRun)
        mode = "jsonl"
    else:
        if args.runs <= 0:
            parser.error("live mode needs --runs > 0")
        try:
            _, runs, retained = _run_live(
                args.profile,
                args.ticker,
                args.date,
                cold=1,
                warm=max(0, args.runs - 1),
                workdir=args.workdir,
                keep_artifacts=args.keep_artifacts,
            )
        except Exception as exc:
            print(f"live token audit could not start: {exc}", file=sys.stderr)
            return 2
        mode = "live"

    table = default_price_table()
    report = build_token_report(args.profile, runs, table)
    hard_limit = (
        args.hard_limit
        if args.hard_limit is not None
        else budget_for_profile(args.profile).hard_limit
    )
    payload = report.model_dump(mode="json")
    payload["mode"] = mode
    payload["hard_limit"] = hard_limit
    payload["artifacts_kept"] = retained is not None
    if retained is not None:
        payload["artifacts_dir"] = str(retained)
    payload["gate_passed"] = None

    failures = _token_gate_failures(report, args)
    code = 0
    if args.assert_gate:
        try:
            assert_token_acceptance(report, hard_limit=hard_limit)
        except AssertionError as exc:
            failures.append(str(exc))
    if failures:
        payload["gate_passed"] = False
        payload["gate_error"] = "; ".join(failures)
        print(f"token audit gate failed: {payload['gate_error']}", file=sys.stderr)
        code = 1
    elif args.assert_gate or any(
        value is not None
        for value in (
            args.assert_p95,
            args.assert_report_coverage,
            args.assert_silent_over_budget,
            args.assert_cost_error,
            args.assert_routed_quality,
        )
    ):
        payload["gate_passed"] = True
    _emit(payload, args.out)
    return code


__all__ = ["bench_latency_main", "token_audit_main"]
