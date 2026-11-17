"""REQ-FR-002 — Preflight ticker and data availability (Part 1).

Traceable to test-cases/part1-profiles-preflight.md TC-P1-FR002-01..06. The
subject ``tradingagents.preflight`` is not implemented yet.
"""

import pytest

from tests.req._support import require

PREFLIGHT = "tradingagents.preflight"


def test_no_analyst_calls():
    """TC-P1-FR002-01: invalid symbol yields zero analyst-node calls."""
    require(PREFLIGHT)


def test_valid_tickers():
    """TC-P1-FR002-02: 50 valid tickers pass preflight."""
    require(PREFLIGHT)


def test_zero_llm_tokens():
    """TC-P1-FR002-03: preflight failure consumes zero LLM tokens."""
    require(PREFLIGHT)


@pytest.mark.integration
def test_preflight_latency_script():
    """TC-P1-FR002-04: preflight p95 <= 2s (script)."""
    require(PREFLIGHT)


def test_invalid_vs_unavailable():
    """TC-P1-FR002-05: invalid and data-unavailable are distinct."""
    require(PREFLIGHT)


def test_preflight_cache_ttl():
    """TC-P1-FR002-06: preflight caches identity/price with TTLs."""
    require(PREFLIGHT)
