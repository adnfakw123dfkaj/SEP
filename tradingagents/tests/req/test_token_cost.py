"""REQ-COST-001 — Tiered token budget and cost report (Part 6).

Traceable to test-cases/part6-perf-cost.md. The cost subject
(``tradingagents.cost``) is not implemented yet.
"""

import pytest

from tests.req._support import require


@pytest.mark.integration
def test_quick_p95_tokens():
    """TC-P6-COST001-01: quick p95 tokens <= 25000."""
    require("tradingagents.cost")


@pytest.mark.integration
def test_standard_p95_tokens():
    """TC-P6-COST001-02: standard p95 tokens <= 60000."""
    require("tradingagents.cost")


@pytest.mark.integration
def test_deep_p95_tokens():
    """TC-P6-COST001-03: deep p95 tokens <= 150000."""
    require("tradingagents.cost")


def test_report_coverage():
    """TC-P6-COST001-04: every run emits a token/cost report."""
    require("tradingagents.cost")


def test_no_silent_over_budget():
    """TC-P6-COST001-05: no silent over-budget run."""
    require("tradingagents.cost")
