"""TC-P6-INT-001..005: cost-controlled run facade with a fake provider."""

import pytest

from tradingagents.contracts.llm_event import RoutePath
from tradingagents.cost.runner import CostControlledRunner

pytestmark = pytest.mark.unit


def test_tc_p6_int_001_quick_run_writes_manifest_fields(
    make_event, synthetic_price_table, budget
):
    """TC-P6-INT-001: a direct run exposes token/cost/route in the manifest."""
    runner = CostControlledRunner(price_table=synthetic_price_table, budget=budget)
    calls = []

    def provider_call():
        calls.append("called")
        return [make_event(prompt_tokens=10, completion_tokens=5, total_tokens=15)]

    result = runner.run(
        run_id="run-1",
        profile="quick",
        estimated_tokens=10,
        provider_call=provider_call,
    )

    assert result.route_path is RoutePath.DIRECT
    assert result.provider_calls == 1
    assert result.manifest["run_id"] == "run-1"
    assert result.manifest["profile"] == "quick"
    assert result.manifest["route_path"] == "direct"
    assert result.manifest["token_usage_by_agent"]["market"] == 15
    assert result.manifest["currency"] == "CNY"
    assert result.manifest["price_table_version"] == synthetic_price_table.version


def test_tc_p6_int_002_soft_route_uses_summarize(
    make_event, synthetic_price_table, budget
):
    """TC-P6-INT-002: between soft and hard, the run uses summarize."""
    runner = CostControlledRunner(price_table=synthetic_price_table, budget=budget)

    result = runner.run(
        run_id="run-1",
        profile="standard",
        estimated_tokens=90,
        provider_call=lambda: [make_event()],
    )

    assert result.route_path is RoutePath.SUMMARIZE
    assert result.manifest["route_path"] == "summarize"
    assert result.provider_calls == 1


def test_tc_p6_int_003_hard_fail_has_no_provider_call(
    make_event, synthetic_price_table, budget
):
    """TC-P6-INT-003: over hard cap, the facade never calls the provider."""
    runner = CostControlledRunner(price_table=synthetic_price_table, budget=budget)
    calls = []

    result = runner.run(
        run_id="run-1",
        profile="quick",
        estimated_tokens=101,
        provider_call=lambda: calls.append("called") or [make_event()],
    )

    assert result.route_path is RoutePath.HARD_FAIL
    assert result.provider_calls == 0
    assert calls == []
    assert result.manifest["status"] == "budget_exceeded"
    assert result.manifest["final_rating"] == "REVIEW"


def test_tc_p6_int_004_cache_hit_is_visible(
    make_event, synthetic_price_table, budget
):
    """TC-P6-INT-004: cache hits are recorded and reduce the run tokens."""
    runner = CostControlledRunner(price_table=synthetic_price_table, budget=budget)

    result = runner.run(
        run_id="run-1",
        profile="quick",
        estimated_tokens=10,
        provider_call=lambda: [
            make_event(
                cache_hit=True,
                prompt_tokens=1,
                completion_tokens=1,
                total_tokens=2,
            )
        ],
    )

    assert result.manifest["cache_hits"] == 1
    assert result.cost_report.total_tokens == 2


def test_tc_p6_int_005_quality_floor_failure_reverts_route(
    make_event, synthetic_price_table, budget
):
    """TC-P6-INT-005: a failed quality floor reverts a non-direct route."""
    runner = CostControlledRunner(price_table=synthetic_price_table, budget=budget)

    result = runner.run(
        run_id="run-1",
        profile="standard",
        estimated_tokens=90,
        provider_call=lambda: [make_event()],
        quality_floor_pass=False,
    )

    assert result.manifest["quality_floor_pass"] is False
    assert result.manifest["cost_route_reverted"] is True
    assert result.route_path is RoutePath.DIRECT


def test_tc_p6_int_006_runner_creates_a_fresh_monitor_per_run(
    make_event, synthetic_price_table, budget
):
    """TC-P6-INT-006: reusing one runner must not carry events into the next run."""
    runner = CostControlledRunner(price_table=synthetic_price_table, budget=budget)

    first = runner.run(
        run_id="r1",
        profile="quick",
        estimated_tokens=10,
        provider_call=lambda: [
            make_event(run_id="r1", prompt_tokens=10, completion_tokens=5, total_tokens=15)
        ],
    )
    second = runner.run(
        run_id="r2",
        profile="quick",
        estimated_tokens=10,
        provider_call=lambda: [
            make_event(run_id="r2", prompt_tokens=20, completion_tokens=10, total_tokens=30)
        ],
    )

    assert first.cost_report.total_tokens == 15
    assert second.cost_report.total_tokens == 30
    assert second.cost_report.by_agent["market"] == 30
