"""TC-P6-BEN-001..007: latency report aggregation and acceptance gates."""

import pytest

from tradingagents.cost.benchmark import (
    LatencySample,
    assert_latency_acceptance,
    policy_for_profile,
    summarize_latency,
)

pytestmark = pytest.mark.unit


def _samples(profile, durations, cache_state="cold"):
    return [
        LatencySample(
            profile=profile,
            cache_state=cache_state,
            duration_s=float(value),
            success=True,
        )
        for value in durations
    ]


def _mixed(profile, cold, warm):
    return _samples(profile, cold, "cold") + _samples(profile, warm, "warm")


def test_tc_p6_ben_001_report_schema():
    """TC-P6-BEN-001: 15 cold + 15 warm produce a complete latency report."""
    report = summarize_latency(
        "quick",
        _mixed("quick", [60] * 15, [40] * 15),
        baseline_p95_s=100.0,
    )

    assert report.profile == "quick"
    assert report.cold_runs == 15
    assert report.warm_runs == 15
    assert report.p50_s > 0
    assert report.p95_s > 0
    assert report.p99_s >= report.p95_s
    assert report.failure_rate == 0.0
    assert report.baseline_p95_s == 100.0
    assert report.improvement == pytest.approx(0.40)


def test_tc_p6_ben_002_quick_standard_relative_improvement():
    """TC-P6-BEN-002: Quick/Standard must improve p95 by at least 30%."""
    passing = summarize_latency(
        "quick",
        _mixed("quick", [69] * 15, [69] * 15),
        baseline_p95_s=100.0,
    )
    failing = summarize_latency(
        "standard",
        _mixed("standard", [71] * 15, [71] * 15),
        baseline_p95_s=100.0,
    )

    assert_latency_acceptance(passing, require_improvement=True, min_improvement=0.30)
    with pytest.raises(AssertionError):
        assert_latency_acceptance(failing, require_improvement=True, min_improvement=0.30)


def test_tc_p6_ben_003_deep_is_record_only():
    """TC-P6-BEN-003: Deep 3+3 is recorded but never blocks on improvement."""
    report = summarize_latency(
        "deep",
        _mixed("deep", [1500, 1600, 1700], [1400, 1450, 1500]),
        baseline_p95_s=1000.0,
    )

    assert report.cold_runs == 3
    assert report.warm_runs == 3
    assert report.p95_s > 0
    assert_latency_acceptance(report, require_improvement=False)


def test_tc_p6_ben_004_p99_is_recorded_not_blocking():
    """TC-P6-BEN-004: p99 is reported; it does not gate acceptance."""
    report = summarize_latency(
        "quick",
        _mixed("quick", [60] * 15, [40] * 15),
        baseline_p95_s=100.0,
    )

    assert report.p99_s >= report.p95_s
    # No assertion on p99/p95 ratio: confirmed record-only.
    assert_latency_acceptance(report, require_improvement=True, min_improvement=0.30)


def test_tc_p6_ben_005_failure_rate_blocks():
    """TC-P6-BEN-005: more than 1% failed runs must fail acceptance."""
    samples = _mixed("quick", [60] * 14 + [0], [40] * 15)
    samples[0] = samples[0].model_copy(update={"success": False})
    report = summarize_latency("quick", samples, baseline_p95_s=100.0)

    assert report.successful_runs == 29
    assert report.failed_runs == 1
    assert report.failure_rate > 0.01
    with pytest.raises(AssertionError):
        assert_latency_acceptance(report, require_improvement=True, min_improvement=0.30)


def test_tc_p6_ben_006_absolute_p95_is_recorded():
    """TC-P6-BEN-006: absolute p95 is present but not a blocking threshold."""
    report = summarize_latency(
        "quick",
        _mixed("quick", [60] * 15, [40] * 15),
        baseline_p95_s=100.0,
    )

    assert report.p95_s == 60
    assert report.p95_s <= 300  # recorded for context only


def test_tc_p6_ben_007_improvement_formula():
    """TC-P6-BEN-007: improvement = (baseline - current) / baseline."""
    pass_report = summarize_latency(
        "quick",
        _mixed("quick", [69] * 15, [69] * 15),
        baseline_p95_s=100.0,
    )
    fail_report = summarize_latency(
        "quick",
        _mixed("quick", [71] * 15, [71] * 15),
        baseline_p95_s=100.0,
    )

    assert pass_report.improvement == pytest.approx(0.31)
    assert fail_report.improvement == pytest.approx(0.29)


def test_tc_p6_ben_008_absolute_p95_warns_without_blocking():
    """TC-P6-BEN-008: absolute p95 over target warns but never raises."""
    report = summarize_latency(
        "deep",
        _mixed("deep", [2000] * 3, [2000] * 3),
        baseline_p95_s=1000.0,
    )

    warnings = assert_latency_acceptance(report)

    assert any("absolute p95" in warning for warning in warnings)


def test_tc_p6_ben_009_policy_table_controls_profile_defaults():
    """TC-P6-BEN-009: Quick requires improvement; Deep is record-only."""
    assert policy_for_profile("quick").require_improvement is True
    assert policy_for_profile("deep").require_improvement is False

    quick = summarize_latency(
        "quick",
        _mixed("quick", [90] * 15, [90] * 15),
        baseline_p95_s=100.0,
    )
    with pytest.raises(AssertionError):
        assert_latency_acceptance(quick)

    deep = summarize_latency(
        "deep",
        _mixed("deep", [1000] * 3, [1000] * 3),
        baseline_p95_s=1000.0,
    )
    assert assert_latency_acceptance(deep) == []
