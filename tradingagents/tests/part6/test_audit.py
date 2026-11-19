"""TC-P6-AUD-001..007: token/cost audit and real price table."""

from datetime import date
from decimal import Decimal

import pytest

from tradingagents.contracts.llm_event import RoutePath
from tradingagents.cost.audit import (
    TokenRun,
    assert_token_acceptance,
    build_token_report,
)
from tradingagents.cost.pricing import default_price_table

pytestmark = pytest.mark.unit


def _run(run_id="run-1", profile="quick", **overrides):
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


def test_tc_p6_aud_001_token_p95_caps(synthetic_price_table):
    """TC-P6-AUD-001: p95 token usage stays under each profile cap."""
    limits = {"quick": 25_000, "standard": 60_000, "deep": 150_000}
    for profile, limit in limits.items():
        runs = [_run(f"{profile}-{i}", profile, total_tokens=1000) for i in range(30)]
        report = build_token_report(profile, runs, synthetic_price_table)

        assert report.p95_tokens == 1000
        assert_token_acceptance(report, hard_limit=limit)


def test_tc_p6_aud_002_report_coverage(synthetic_price_table):
    """TC-P6-AUD-002: every run must contribute a token/cost report."""
    runs = [_run(f"r{i}") for i in range(29)] + [_run("r29", has_report=False)]
    report = build_token_report("quick", runs, synthetic_price_table)

    assert report.report_coverage == pytest.approx(29 / 30)
    with pytest.raises(AssertionError):
        assert_token_acceptance(report, hard_limit=25_000)


def test_tc_p6_aud_003_no_silent_over_budget(synthetic_price_table):
    """TC-P6-AUD-003: silent over-budget runs fail acceptance."""
    runs = [_run(f"r{i}") for i in range(29)] + [_run("r29", silent_over_budget=True)]
    report = build_token_report("quick", runs, synthetic_price_table)

    assert report.silent_over_budget_runs == 1
    with pytest.raises(AssertionError):
        assert_token_acceptance(report, hard_limit=25_000)


def test_tc_p6_aud_004_cost_error(synthetic_price_table):
    """TC-P6-AUD-004: reported cost is within 5% of usage x price table."""
    good = build_token_report(
        "quick",
        [_run(cost=Decimal("100"), cost_ground_truth=Decimal("100"))],
        synthetic_price_table,
    )
    bad = build_token_report(
        "quick",
        [_run(cost=Decimal("106"), cost_ground_truth=Decimal("100"))],
        synthetic_price_table,
    )

    assert good.cost_relative_error == pytest.approx(0.0)
    assert bad.cost_relative_error == pytest.approx(0.06)
    with pytest.raises(AssertionError):
        assert_token_acceptance(bad, hard_limit=25_000)


def test_tc_p6_aud_005_routed_quality_floor(synthetic_price_table):
    """TC-P6-AUD-005: every routed run must pass the quality floor."""
    routed = _run(route_paths=[RoutePath.SUMMARIZE], quality_floor_pass=True)
    failed = _run(route_paths=[RoutePath.CHEAPER_MODEL], quality_floor_pass=False)

    good = build_token_report("quick", [routed], synthetic_price_table)
    bad = build_token_report("quick", [routed, failed], synthetic_price_table)

    assert good.routed_quality_floor_pass_rate == 1.0
    assert bad.routed_quality_floor_pass_rate == 0.5
    with pytest.raises(AssertionError):
        assert_token_acceptance(bad, hard_limit=25_000)


def test_tc_p6_aud_006_price_table_provenance(synthetic_price_table):
    """TC-P6-AUD-006: report records CNY, price table version and source."""
    report = build_token_report("quick", [_run()], synthetic_price_table)

    assert report.currency == "CNY"
    assert report.price_table_version == synthetic_price_table.version
    assert report.price_table_source == synthetic_price_table.source_url


def test_tc_p6_aud_007_real_deepseek_price_table():
    """TC-P6-AUD-007: official DeepSeek CNY prices are encoded exactly."""
    table = default_price_table()

    assert table.currency == "CNY"
    assert "api-docs.deepseek.com" in table.source_url
    assert table.retrieved_at == date(2026, 11, 16)

    flash = table.models["deepseek-flash"]
    assert flash.model_version == "DeepSeek-V4.1-Flash-1017"
    assert flash.off_peak.input_cache_miss_per_1m == Decimal("1")
    assert flash.off_peak.output_per_1m == Decimal("4")
    assert flash.peak.input_cache_miss_per_1m == Decimal("2")
    assert flash.peak.output_per_1m == Decimal("8")

    pro = table.models["deepseek-v4-pro"]
    assert pro.model_version == "DeepSeek-V4-Pro-0813"
    assert pro.off_peak.input_cache_miss_per_1m == Decimal("4.5")
    assert pro.off_peak.output_per_1m == Decimal("13.5")
    assert pro.peak.input_cache_miss_per_1m == Decimal("9")
    assert pro.peak.output_per_1m == Decimal("27")


def test_tc_p6_aud_008_cost_error_uses_worst_run(synthetic_price_table):
    """TC-P6-AUD-008: one 6% run must fail even if the rest are perfect."""
    runs = [_run(f"r{i}") for i in range(9)]
    runs.append(_run("bad", cost=Decimal("106"), cost_ground_truth=Decimal("100")))

    report = build_token_report("quick", runs, synthetic_price_table)

    assert report.cost_relative_error == pytest.approx(0.06)
    with pytest.raises(AssertionError):
        assert_token_acceptance(report, hard_limit=25_000)
