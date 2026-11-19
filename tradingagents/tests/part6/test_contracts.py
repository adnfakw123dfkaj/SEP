"""TC-P6-CON-001..006: contract tests for Part 6 data structures."""

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tradingagents.contracts.cost import Budget, CostReport, TokenEstimate
from tradingagents.contracts.llm_event import (
    CallStatus,
    LLMCallEvent,
    RoutePath,
    UsageSource,
)

pytestmark = pytest.mark.unit


def test_tc_p6_con_001_event_required_fields(make_event):
    """TC-P6-CON-001: every LLMCallEvent carries the fields downstream needs."""
    event = make_event()

    assert event.event_id == "event-1"
    assert event.run_id == "run-1"
    assert event.call_id == "call-1"
    assert event.agent_name == "market"
    assert event.model == "model-a"
    assert event.provider == "test-provider"
    assert event.prompt_tokens == 10
    assert event.completion_tokens == 5
    assert event.total_tokens == 15
    assert event.latency_ms == 100.0
    assert event.status is CallStatus.SUCCESS
    assert event.route_path is RoutePath.DIRECT
    assert event.usage_source is UsageSource.PROVIDER
    assert event.timestamp.tzinfo is not None
    assert event.tool_name == "tool-x"


def test_tc_p6_con_002_token_sum_consistency(shanghai):
    """TC-P6-CON-002: total_tokens must equal prompt + completion."""
    base = {
        "event_id": "e",
        "run_id": "r",
        "call_id": "c",
        "agent_name": "market",
        "model": "model-a",
        "provider": "p",
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "latency_ms": 1.0,
        "status": CallStatus.SUCCESS,
        "retry_count": 0,
        "route_path": RoutePath.DIRECT,
        "usage_source": UsageSource.PROVIDER,
        "timestamp": datetime(2026, 11, 16, 10, 0, tzinfo=shanghai),
    }

    with pytest.raises(ValidationError):
        LLMCallEvent(**base, total_tokens=16)

    with pytest.raises(ValidationError):
        LLMCallEvent(**{**base, "prompt_tokens": -1}, total_tokens=4)


def test_tc_p6_con_003_status_and_route_enums(make_event):
    """TC-P6-CON-003: status/route values are closed enums."""
    for status in CallStatus:
        assert make_event(status=status).status is status

    for route in RoutePath:
        assert make_event(route_path=route).route_path is route

    with pytest.raises(ValidationError):
        make_event(status="not-a-status")

    with pytest.raises(ValidationError):
        make_event(route_path="not-a-route")


def test_tc_p6_con_004_token_estimate_structure():
    """TC-P6-CON-004: TokenEstimate is internally consistent."""
    estimate = TokenEstimate(
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        confidence="medium",
    )
    assert estimate.total_tokens == estimate.input_tokens + estimate.output_tokens
    assert estimate.confidence == "medium"

    with pytest.raises(ValidationError):
        TokenEstimate(input_tokens=10, output_tokens=5, total_tokens=16, confidence="medium")

    with pytest.raises(ValidationError):
        TokenEstimate(input_tokens=-1, output_tokens=5, total_tokens=4, confidence="low")


def test_tc_p6_con_005_budget_structure():
    """TC-P6-CON-005: Budget uses CNY and enforces soft <= hard."""
    budget = Budget(profile="quick", soft_limit=80, hard_limit=100, currency="CNY")
    assert budget.currency == "CNY"
    assert budget.soft_limit <= budget.hard_limit

    with pytest.raises(ValidationError):
        Budget(profile="quick", soft_limit=101, hard_limit=100, currency="CNY")

    with pytest.raises(ValidationError):
        Budget(profile="quick", soft_limit=0, hard_limit=100, currency="CNY")


def test_tc_p6_con_006_cost_report_structure():
    """TC-P6-CON-006: CostReport exposes all fields the manifest/audit need."""
    report = CostReport(
        run_id="run-1",
        profile="quick",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        by_agent={"market": 15},
        by_model={"model-a": 15},
        by_tool={"tool-x": 15},
        cost=Decimal("0.0001"),
        currency="CNY",
        price_table_version="synthetic-v1",
        price_table_source="https://example.test/pricing",
        peak_policy="weekday_hours_ignore_holidays",
        cache_policy="cache_miss",
        coverage=1.0,
        over_budget=False,
        route_paths=[RoutePath.DIRECT],
        quality_floor_pass=True,
    )

    assert report.currency == "CNY"
    assert report.price_table_version == "synthetic-v1"
    assert report.price_table_source
    assert report.peak_policy
    assert report.cache_policy == "cache_miss"
    assert report.route_paths == [RoutePath.DIRECT]
