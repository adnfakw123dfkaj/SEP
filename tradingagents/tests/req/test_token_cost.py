"""REQ-COST-001 — Tiered token budget and cost report (Part 6).

Traceable to test-cases/part6-perf-cost.md. Exercises the implemented cost
surface directly: the per-profile budget caps, the cost report build/acceptance,
and the hard-stop enforcement path. The verbatim ``--assert-*`` script commands
(``scripts/token_audit.py``) live in the SCRIPT/integration cases; these are the
offline unit-level checks over the same behaviour.
"""

from decimal import Decimal

import pytest

from tradingagents.contracts.cost import Budget
from tradingagents.contracts.llm_event import RoutePath
from tradingagents.cost.audit import TokenRun, assert_token_acceptance, build_token_report
from tradingagents.cost.budget import budget_for_profile
from tradingagents.cost.enforcement import BudgetExceededError, guarded_call, handle_budget_exceeded
from tradingagents.cost.monitor import CostMonitor
from tradingagents.cost.pricing import default_price_table

pytestmark = pytest.mark.unit


def _run(run_id="r", profile="quick", **overrides):
    data = {
        "run_id": run_id,
        "profile": profile,
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


# --- TC-P6-COST001-01..03: per-profile token caps -------------------------


def test_quick_p95_tokens():
    """TC-P6-COST001-01: quick p95 tokens <= 25000."""
    assert budget_for_profile("quick").hard_limit == 25_000
    runs = [_run(f"q{i}", "quick", total_tokens=1000) for i in range(30)]
    report = build_token_report("quick", runs, default_price_table())
    assert_token_acceptance(report, hard_limit=25_000)


def test_standard_p95_tokens():
    """TC-P6-COST001-02: standard p95 tokens <= 60000."""
    assert budget_for_profile("standard").hard_limit == 60_000


def test_deep_p95_tokens():
    """TC-P6-COST001-03: deep p95 tokens <= 150000."""
    assert budget_for_profile("deep").hard_limit == 150_000


# --- TC-P6-COST001-04: every run emits a report ---------------------------


def test_report_coverage():
    """TC-P6-COST001-04: a run without a report drops coverage below 1.0."""
    runs = [_run(f"r{i}") for i in range(29)] + [_run("r29", has_report=False)]
    report = build_token_report("quick", runs, default_price_table())
    assert report.report_coverage == pytest.approx(29 / 30)
    with pytest.raises(AssertionError):
        assert_token_acceptance(report, hard_limit=25_000)


# --- TC-P6-COST001-05: no silent over-budget ------------------------------


def test_no_silent_over_budget():
    """TC-P6-COST001-05: a silent over-budget run fails acceptance."""
    runs = [_run(f"r{i}") for i in range(29)] + [_run("r29", silent_over_budget=True)]
    report = build_token_report("quick", runs, default_price_table())
    assert report.silent_over_budget_runs == 1
    with pytest.raises(AssertionError):
        assert_token_acceptance(report, hard_limit=25_000)


def test_hard_stop_blocks_call_over_budget():
    """The wired enforcement raises before the provider call would exceed hard."""
    budget = Budget(profile="quick", soft_limit=20_000, hard_limit=25_000, currency="CNY")
    calls = []
    with pytest.raises(BudgetExceededError):
        guarded_call(budget.hard_limit + 1, budget, lambda: calls.append(1))
    assert calls == []  # the provider call never happened


def test_budget_exceeded_record_is_review():
    """A hard breach is recorded as budget_exceeded / REVIEW, never a trade."""
    budget = Budget(profile="quick", soft_limit=20_000, hard_limit=25_000, currency="CNY")
    monitor = CostMonitor(default_price_table())
    record = handle_budget_exceeded("run-1", budget.hard_limit + 1, budget, monitor)
    assert record.status == "budget_exceeded"
    assert record.final_rating == "REVIEW"


# --- TC-P6-COST001-08: routed-run quality floor ---------------------------


def test_routed_quality_floor():
    """TC-P6-COST001-08: every routed run (non-DIRECT) must pass its quality floor."""
    routed_ok = _run("ok", route_paths=[RoutePath.SUMMARIZE], quality_floor_pass=True)
    routed_fail = _run("fail", route_paths=[RoutePath.CHEAPER_MODEL], quality_floor_pass=False)
    good_report = build_token_report("quick", [routed_ok], default_price_table())
    bad_report = build_token_report("quick", [routed_ok, routed_fail], default_price_table())
    assert good_report.routed_quality_floor_pass_rate == 1.0
    assert bad_report.routed_quality_floor_pass_rate == 0.5
    with pytest.raises(AssertionError):
        assert_token_acceptance(bad_report, hard_limit=25_000)
