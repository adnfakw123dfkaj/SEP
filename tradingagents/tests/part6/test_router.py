"""TC-P6-RTR-001..009: budget routing and protected evidence."""

import pytest

from tradingagents.contracts.llm_event import RoutePath
from tradingagents.cost.router import (
    route,
    route_after_summary,
    select_cheaper_model,
    summarize_context,
)

pytestmark = pytest.mark.unit


def test_tc_p6_rtr_001_within_soft_goes_direct(budget):
    """TC-P6-RTR-001: under the soft limit, call directly."""
    decision = route(10, budget)

    assert decision.route_path is RoutePath.DIRECT
    assert decision.estimated_tokens == 10


def test_tc_p6_rtr_002_between_soft_and_hard_summarizes(budget):
    """TC-P6-RTR-002: between soft and hard, summarize first."""
    decision = route(90, budget)

    assert decision.route_path is RoutePath.SUMMARIZE
    assert decision.estimated_tokens == 90


def test_tc_p6_rtr_003_over_hard_fails_fast(budget):
    """TC-P6-RTR-003: over the hard cap, stop before any provider call."""
    decision = route(101, budget)

    assert decision.route_path is RoutePath.HARD_FAIL
    assert decision.estimated_tokens == 101


def test_tc_p6_rtr_004_summary_preserves_protected_evidence():
    """TC-P6-RTR-004: summarization never drops decision-critical evidence."""
    context = {
        "market_snapshot": "NVDA close=168.89; rsi=23.95",
        "evidence_refs": ["market_snapshot:abc", "news:123"],
        "risk_constraints": ["max 1% account risk"],
        "rating_inputs": {"rating": "Sell"},
        "news_text": "long news " * 200,
    }
    protected = {
        "market_snapshot",
        "evidence_refs",
        "risk_constraints",
        "rating_inputs",
    }

    summary = summarize_context(context, protected_keys=protected)

    for key in protected:
        assert summary[key] == context[key]


def test_tc_p6_rtr_005_route_records_path_and_reason(budget):
    """TC-P6-RTR-005: route decisions are auditable."""
    decision = route(90, budget)

    assert decision.route_path is RoutePath.SUMMARIZE
    assert isinstance(decision.reason, str) and decision.reason
    assert decision.estimated_tokens == 90


def test_tc_p6_rtr_006_over_hard_is_not_silent(budget):
    """TC-P6-RTR-006: hard failure is explicit, never a silent overrun."""
    decision = route(101, budget)

    assert decision.route_path is RoutePath.HARD_FAIL
    assert "budget" in decision.reason.lower() or "hard" in decision.reason.lower()


def test_tc_p6_rtr_007_after_summary_uses_cheaper_model(budget):
    """TC-P6-RTR-007: if summarization is still above soft, try a cheaper model."""
    assert route_after_summary(10, budget).route_path is RoutePath.DIRECT
    assert route_after_summary(90, budget).route_path is RoutePath.CHEAPER_MODEL
    assert route_after_summary(101, budget).route_path is RoutePath.HARD_FAIL


def test_tc_p6_rtr_008_summary_reduces_context():
    """TC-P6-RTR-008: summarization must actually reduce the context."""
    context = {
        "market_snapshot": "NVDA close=168.89",
        "news_text": "long news " * 500,
    }

    summary = summarize_context(context, protected_keys={"market_snapshot"})

    assert summary["market_snapshot"] == context["market_snapshot"]
    assert len(str(summary["news_text"])) < len(str(context["news_text"]))


def test_tc_p6_rtr_009_cheaper_model_is_actually_cheaper(synthetic_price_table):
    """TC-P6-RTR-009: cheaper_model selects a lower-priced allowed model."""
    selected = select_cheaper_model(
        "model-a",
        price_table=synthetic_price_table,
        allowed_models={"model-a", "model-b"},
    )

    assert selected == "model-b"
    assert (
        synthetic_price_table.models[selected].off_peak.input_cache_miss_per_1m
        < synthetic_price_table.models["model-a"].off_peak.input_cache_miss_per_1m
    )
