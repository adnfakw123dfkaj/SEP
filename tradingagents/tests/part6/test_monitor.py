"""TC-P6-MON-001..012: cost aggregation, pricing phase, percentiles."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from tradingagents.contracts.llm_event import UsageSource
from tradingagents.cost.monitor import CostMonitor, nearest_rank, price_phase
from tradingagents.cost.report import compute_report_coverage

pytestmark = pytest.mark.unit


def _report(monitor, budget):
    return monitor.report("run-1", budget, quality_floor_pass=True)


def test_tc_p6_mon_001_aggregates_by_agent(make_event, synthetic_price_table, budget):
    """TC-P6-MON-001: per-agent token totals are correct."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(make_event(agent_name="market", prompt_tokens=10, completion_tokens=5, total_tokens=15))
    monitor.record(make_event(agent_name="news", prompt_tokens=20, completion_tokens=10, total_tokens=30))

    report = _report(monitor, budget)

    assert report.by_agent["market"] == 15
    assert report.by_agent["news"] == 30
    assert report.total_tokens == 45


def test_tc_p6_mon_002_aggregates_by_model(make_event, synthetic_price_table, budget):
    """TC-P6-MON-002: per-model token totals and costs are correct."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(make_event(model="model-a", prompt_tokens=10, completion_tokens=5, total_tokens=15))
    monitor.record(make_event(model="model-b", prompt_tokens=20, completion_tokens=10, total_tokens=30))

    report = _report(monitor, budget)

    assert report.by_model["model-a"] == 15
    assert report.by_model["model-b"] == 30
    assert report.total_tokens == 45


def test_tc_p6_mon_003_retry_tokens_are_included(make_event, synthetic_price_table, budget):
    """TC-P6-MON-003: retry tokens count toward the run total."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(
        make_event(
            retry_count=2,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    report = _report(monitor, budget)

    assert report.total_tokens == 15
    assert report.by_agent["market"] == 15


def test_tc_p6_mon_004_cost_math_uses_phase_and_cache_miss(
    make_event, synthetic_price_table, budget
):
    """TC-P6-MON-004: cost = input*cache_miss + output, divided by 1M."""
    peak = datetime(2026, 11, 16, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    off_peak = datetime(2026, 11, 16, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(
        make_event(
            timestamp=peak,
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            total_tokens=2_000_000,
        )
    )
    monitor.record(
        make_event(
            timestamp=off_peak,
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            total_tokens=2_000_000,
        )
    )

    report = _report(monitor, budget)

    # model-a: peak 2+8=10 CNY; off-peak 1+4=5 CNY.
    assert report.cost == Decimal("15")


def test_tc_p6_mon_005_missing_usage_falls_back(make_event, synthetic_price_table, budget):
    """TC-P6-MON-005: estimated usage still produces a report."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(
        make_event(
            usage_source=UsageSource.ESTIMATED,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    report = _report(monitor, budget)

    assert report.total_tokens == 15
    assert report.by_agent["market"] == 15


def test_tc_p6_mon_006_price_table_provenance(make_event, synthetic_price_table, budget):
    """TC-P6-MON-006: reports pin the price table version and source."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(make_event())

    report = _report(monitor, budget)

    assert report.price_table_version == synthetic_price_table.version
    assert report.price_table_source == synthetic_price_table.source_url
    assert report.currency == "CNY"


def test_tc_p6_mon_007_report_coverage():
    """TC-P6-MON-007: coverage is the fraction of runs with a report."""
    assert compute_report_coverage({"r1", "r2"}, {"r1", "r2"}) == 1.0
    assert compute_report_coverage({"r1", "r2"}, {"r1"}) == 0.5


def test_tc_p6_mon_008_empty_event_set(synthetic_price_table, budget):
    """TC-P6-MON-008: an empty run produces zeros, not an exception."""
    monitor = CostMonitor(synthetic_price_table)

    report = _report(monitor, budget)

    assert report.total_tokens == 0
    assert report.cost == Decimal("0")


def test_tc_p6_mon_009_nearest_rank_percentile():
    """TC-P6-MON-009: p50/p95 use nearest-rank, not interpolation."""
    values = list(range(1, 101))

    assert nearest_rank(values, 0.50) == 50
    assert nearest_rank(values, 0.95) == 95


def test_tc_p6_mon_010_price_phase_weekday_and_weekend(shanghai):
    """TC-P6-MON-010: peak is 09-12 and 14-18 on weekdays; weekends are off-peak."""
    assert price_phase(datetime(2026, 11, 16, 9, 0, tzinfo=shanghai)) == "peak"
    assert price_phase(datetime(2026, 11, 16, 12, 0, tzinfo=shanghai)) == "off_peak"
    assert price_phase(datetime(2026, 11, 16, 14, 0, tzinfo=shanghai)) == "peak"
    assert price_phase(datetime(2026, 11, 16, 18, 0, tzinfo=shanghai)) == "off_peak"
    assert price_phase(datetime(2026, 11, 14, 10, 0, tzinfo=shanghai)) == "off_peak"


def test_tc_p6_mon_011_peak_costs_more_than_off_peak(
    make_event, synthetic_price_table, budget
):
    """TC-P6-MON-011: identical tokens cost more in the peak phase."""
    peak = datetime(2026, 11, 16, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    off_peak = datetime(2026, 11, 16, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    peak_monitor = CostMonitor(synthetic_price_table)
    peak_monitor.record(make_event(timestamp=peak, prompt_tokens=1000, completion_tokens=1000, total_tokens=2000))
    off_peak_monitor = CostMonitor(synthetic_price_table)
    off_peak_monitor.record(make_event(timestamp=off_peak, prompt_tokens=1000, completion_tokens=1000, total_tokens=2000))

    assert _report(peak_monitor, budget).cost > _report(off_peak_monitor, budget).cost


def test_tc_p6_mon_012_holidays_are_ignored(make_event, synthetic_price_table, budget):
    """TC-P6-MON-012: a weekday holiday is still priced by weekday hours."""
    holiday_peak = datetime(2026, 10, 1, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(make_event(timestamp=holiday_peak, prompt_tokens=1000, completion_tokens=1000, total_tokens=2000))

    report = _report(monitor, budget)

    assert price_phase(holiday_peak) == "peak"
    assert report.peak_policy == "weekday_hours_ignore_holidays"


def test_tc_p6_mon_013_reports_are_isolated_by_run_id(
    make_event, synthetic_price_table, budget
):
    """TC-P6-MON-013: a shared monitor must not leak events across runs."""
    monitor = CostMonitor(synthetic_price_table)
    monitor.record(
        make_event(
            run_id="r1",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )
    monitor.record(
        make_event(
            run_id="r2",
            prompt_tokens=20,
            completion_tokens=10,
            total_tokens=30,
        )
    )

    r1 = monitor.report("r1", budget, quality_floor_pass=True)
    r2 = monitor.report("r2", budget, quality_floor_pass=True)

    assert r1.total_tokens == 15
    assert r2.total_tokens == 30
    assert r1.by_agent["market"] == 15
    assert r2.by_agent["market"] == 30
