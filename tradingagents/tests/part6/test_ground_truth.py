"""Independent provider-usage cost calculation for the audit gate."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from tradingagents.contracts.llm_event import CallStatus, UsageSource
from tradingagents.cost.ground_truth import provider_ground_truth_cost

pytestmark = pytest.mark.unit


def test_ground_truth_recomputes_peak_and_off_peak(make_event, synthetic_price_table):
    peak = datetime(2026, 11, 16, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    off_peak = datetime(2026, 11, 16, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    events = [
        make_event(
            timestamp=peak,
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            total_tokens=2_000_000,
        ),
        make_event(
            timestamp=off_peak,
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            total_tokens=2_000_000,
        ),
    ]

    assert provider_ground_truth_cost(events, synthetic_price_table) == Decimal("15")


def test_ground_truth_rejects_estimated_usage(make_event, synthetic_price_table):
    event = make_event(usage_source=UsageSource.ESTIMATED)

    assert provider_ground_truth_cost([event], synthetic_price_table) is None


def test_ground_truth_rejects_unknown_models(make_event, synthetic_price_table):
    event = make_event(model="not-priced")

    assert provider_ground_truth_cost([event], synthetic_price_table) is None


def test_ground_truth_ignores_failed_calls(make_event, synthetic_price_table):
    failed = make_event(
        status=CallStatus.FAILURE,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
    )
    success = make_event()

    assert provider_ground_truth_cost([failed, success], synthetic_price_table) == Decimal(
        "0.00006"
    )


def test_ground_truth_filters_by_run_id(make_event, synthetic_price_table):
    events = [
        make_event(run_id="run-1"),
        make_event(
            run_id="run-2",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            total_tokens=2_000_000,
        ),
    ]

    assert provider_ground_truth_cost(
        events, synthetic_price_table, run_id="run-1"
    ) == Decimal("0.00006")
