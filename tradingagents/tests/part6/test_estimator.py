"""TC-P6-EST-001..006: token estimation behaviour."""

import pytest

from tradingagents.cost.estimator import estimate_tokens

pytestmark = pytest.mark.unit


def test_tc_p6_est_001_normal_prompt():
    """TC-P6-EST-001: a normal prompt returns a consistent estimate."""
    estimate = estimate_tokens("Analyse NVDA for 2026-11-16.", model="deepseek-flash")

    assert estimate.input_tokens > 0
    assert estimate.output_tokens >= 0
    assert estimate.total_tokens == estimate.input_tokens + estimate.output_tokens
    assert estimate.confidence in {"low", "medium", "high"}


def test_tc_p6_est_002_empty_and_tiny_input():
    """TC-P6-EST-002: empty/very short input never produces negative tokens."""
    empty = estimate_tokens("", model="deepseek-flash")
    tiny = estimate_tokens("a", model="deepseek-flash")

    assert empty.input_tokens == 0
    assert empty.total_tokens == 0
    assert tiny.input_tokens >= 0
    assert tiny.total_tokens == tiny.input_tokens + tiny.output_tokens


def test_tc_p6_est_003_long_context_grows():
    """TC-P6-EST-003: a longer context estimates more input tokens."""
    short = estimate_tokens("NVDA earnings.", model="deepseek-flash")
    long = estimate_tokens("NVDA earnings. " * 500, model="deepseek-flash")

    assert long.input_tokens > short.input_tokens


def test_tc_p6_est_004_unknown_model_falls_back():
    """TC-P6-EST-004: unknown model uses a low-confidence fallback."""
    estimate = estimate_tokens("NVDA", model="totally-unknown-model")

    assert estimate.confidence == "low"
    assert estimate.total_tokens == estimate.input_tokens + estimate.output_tokens


def test_tc_p6_est_005_is_deterministic():
    """TC-P6-EST-005: repeated calls with the same input are stable."""
    values = [
        estimate_tokens("NVDA risk review", model="deepseek-flash").model_dump()
        for _ in range(10)
    ]

    assert all(value == values[0] for value in values)


def test_tc_p6_est_006_respects_output_cap():
    """TC-P6-EST-006: an explicit output cap is respected."""
    estimate = estimate_tokens(
        "NVDA risk review",
        model="deepseek-flash",
        max_output_tokens=10,
    )

    assert estimate.output_tokens <= 10
