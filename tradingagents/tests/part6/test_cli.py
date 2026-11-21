"""Step 10b: offline CLI wrappers for latency and token audits."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

import tradingagents.cost.cli as cost_cli
from tradingagents.contracts.llm_event import RoutePath
from tradingagents.cost.audit import TokenRun
from tradingagents.cost.benchmark import LatencySample
from tradingagents.cost.cli import bench_latency_main, token_audit_main

pytestmark = pytest.mark.unit


def _write_latency(path: Path, profile: str, duration: float, baseline: float):
    samples = [
        LatencySample(
            profile=profile,
            cache_state="cold" if index < 15 else "warm",
            duration_s=duration,
            success=True,
        )
        for index in range(30)
    ]
    path.write_text(
        "\n".join(sample.model_dump_json() for sample in samples) + "\n",
        encoding="utf-8",
    )
    return baseline


def _token_run(run_id: str, **overrides):
    data = {
        "run_id": run_id,
        "profile": "quick",
        "total_tokens": 1000,
        "has_report": True,
        "silent_over_budget": False,
        "cost": Decimal("1"),
        "cost_ground_truth": Decimal("1"),
        "quality_floor_pass": True,
        "route_paths": [RoutePath.DIRECT],
    }
    data.update(overrides)
    return TokenRun(**data)


def _write_tokens(path: Path, runs):
    path.write_text(
        "\n".join(run.model_dump_json() for run in runs) + "\n",
        encoding="utf-8",
    )


def test_tc_p6_cli_001_bench_latency_passes(tmp_path):
    """TC-P6-CLI-001: offline latency samples produce a passing report."""
    samples = tmp_path / "latency.jsonl"
    out = tmp_path / "latency.json"
    baseline = _write_latency(samples, "quick", 60.0, 100.0)

    code = bench_latency_main(
        [
            "--profile",
            "quick",
            "--samples-jsonl",
            str(samples),
            "--baseline-p95-s",
            str(baseline),
            "--assert",
            "--out",
            str(out),
        ]
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["gate_passed"] is True
    assert payload["p95_s"] == 60.0
    assert payload["successful_runs"] == 30
    assert payload["failed_runs"] == 0


def test_tc_p6_cli_002_bench_latency_fails(tmp_path):
    """TC-P6-CLI-002: a failing gate returns non-zero and still writes a report."""
    samples = tmp_path / "latency.jsonl"
    out = tmp_path / "latency.json"
    baseline = _write_latency(samples, "quick", 90.0, 100.0)

    code = bench_latency_main(
        [
            "--profile",
            "quick",
            "--samples-jsonl",
            str(samples),
            "--baseline-p95-s",
            str(baseline),
            "--assert",
            "--out",
            str(out),
        ]
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1
    assert payload["gate_passed"] is False
    assert "gate_error" in payload


def test_tc_p6_cli_003_token_audit_passes_with_alias(tmp_path):
    """TC-P6-CLI-003: --events-jsonl is an alias for token runs."""
    runs_path = tmp_path / "runs.jsonl"
    out = tmp_path / "audit.json"
    _write_tokens(runs_path, [_token_run(f"r{i}") for i in range(30)])

    code = token_audit_main(
        [
            "--profile",
            "quick",
            "--events-jsonl",
            str(runs_path),
            "--assert",
            "--out",
            str(out),
        ]
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["gate_passed"] is True
    assert payload["report_coverage"] == 1.0
    assert payload["p95_tokens"] == 1000
    assert payload["currency"] == "CNY"


def test_live_latency_mode_uses_formal_flags(monkeypatch, tmp_path):
    samples = [
        LatencySample(
            profile="quick",
            cache_state="cold" if i < 15 else "warm",
            duration_s=60.0,
            success=True,
        )
        for i in range(30)
    ]
    monkeypatch.setattr(cost_cli, "_run_live", lambda *a, **k: (samples, []))

    out = tmp_path / "live-latency.json"
    code = bench_latency_main([
        "--profile", "quick", "--cold", "15", "--warm", "15",
        "--assert-p95", "300", "--out", str(out),
    ])

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["mode"] == "live"
    assert payload["gate_passed"] is True


def test_live_token_mode_uses_formal_flags(monkeypatch, tmp_path):
    runs = [_token_run(f"live-{i}") for i in range(30)]
    monkeypatch.setattr(cost_cli, "_run_live", lambda *a, **k: ([], runs))

    out = tmp_path / "live-tokens.json"
    code = token_audit_main([
        "--profile", "quick", "--runs", "30", "--assert-p95", "25000",
        "--assert-report-coverage", "1.0", "--assert-silent-over-budget", "0",
        "--assert-cost-error", "0.05", "--assert-routed-quality", "1.0",
        "--out", str(out),
    ])

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["mode"] == "live"
    assert payload["gate_passed"] is True


def test_tc_p6_cli_004_token_audit_fails(tmp_path):
    """TC-P6-CLI-004: silent over-budget makes the audit exit non-zero."""
    runs_path = tmp_path / "runs.jsonl"
    out = tmp_path / "audit.json"
    runs = [_token_run(f"r{i}") for i in range(29)]
    runs.append(_token_run("bad", silent_over_budget=True))
    _write_tokens(runs_path, runs)

    code = token_audit_main(
        [
            "--profile",
            "quick",
            "--runs-jsonl",
            str(runs_path),
            "--assert",
            "--out",
            str(out),
        ]
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1
    assert payload["gate_passed"] is False
    assert payload["silent_over_budget_runs"] == 1
