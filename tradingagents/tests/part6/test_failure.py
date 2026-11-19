"""TC-P6-FAIL-001..006: hard-fail, retry, and quality-floor behaviour."""

import pytest

from tradingagents.contracts.llm_event import CallStatus, RoutePath, UsageSource
from tradingagents.cost.enforcement import (
    BudgetExceededError,
    apply_quality_floor,
    guarded_call,
    handle_budget_exceeded,
)
from tradingagents.cost.monitor import CostMonitor
from tradingagents.cost.report import compute_report_coverage
from tradingagents.cost.router import route

pytestmark = pytest.mark.unit


def test_tc_p6_fail_001_hard_fail_writes_record(make_event, synthetic_price_table, budget):
    """TC-P6-FAIL-001: hard failure returns non-zero and writes a record."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(make_event())

    result = handle_budget_exceeded(
        run_id="run-1",
        estimated_tokens=101,
        budget=budget,
        monitor=monitor,
    )

    assert result.status == "budget_exceeded"
    assert result.exit_code != 0
    assert result.cost_report.over_budget is True
    assert result.cost_report.total_tokens == 15


def test_tc_p6_fail_002_hard_fail_has_no_committed_rating(
    make_event, synthetic_price_table, budget
):
    """TC-P6-FAIL-002: hard failure uses the REVIEW sentinel, never a trade rating."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(make_event())

    result = handle_budget_exceeded("run-1", 101, budget, monitor)

    assert result.final_rating == "REVIEW"
    assert result.final_rating not in {"Buy", "Overweight", "Hold", "Underweight", "Sell"}


def test_tc_p6_fail_003_hard_fail_does_not_call_provider(budget):
    """TC-P6-FAIL-003: the guard stops before the provider call."""
    calls = []

    def provider_call():
        calls.append("called")
        return "should not happen"

    with pytest.raises(BudgetExceededError):
        guarded_call(101, budget, provider_call)

    assert calls == []


def test_tc_p6_fail_004_provider_failure_is_recorded(make_event, synthetic_price_table, budget):
    """TC-P6-FAIL-004: failure/retry events are still accounted for."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(
        make_event(
            status=CallStatus.FAILURE,
            retry_count=2,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    report = monitor.report("run-1", budget, quality_floor_pass=True)

    assert report.total_tokens == 15
    assert report.by_agent["market"] == 15


def test_tc_p6_fail_005_quality_floor_reverts_route(budget):
    """TC-P6-FAIL-005: a routed run that fails quality is reverted."""
    decision = route(90, budget)
    assert decision.route_path is RoutePath.SUMMARIZE

    reverted = apply_quality_floor(decision, quality_floor_pass=False)

    assert reverted.route_path is RoutePath.DIRECT
    assert "revert" in reverted.reason.lower()


def test_tc_p6_fail_006_missing_usage_still_has_coverage(
    make_event, synthetic_price_table, budget
):
    """TC-P6-FAIL-006: estimated usage does not reduce report coverage."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(
        make_event(
            usage_source=UsageSource.ESTIMATED,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    report = monitor.report("run-1", budget, quality_floor_pass=True)

    assert report.total_tokens == 15
    assert compute_report_coverage({"run-1"}, {"run-1"}) == 1.0
