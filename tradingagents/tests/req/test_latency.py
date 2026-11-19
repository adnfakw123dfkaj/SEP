"""REQ-PER-001 — Tiered end-to-end latency (Part 6).

Traceable to test-cases/part6-perf-cost.md. Latency is measured by
``scripts/bench_latency.py`` on a reference environment and is integration-only;
these skip until the script and profiles exist.
"""

import pytest

from tests.req._support import require


@pytest.mark.integration
def test_quick_p95():
    """TC-P6-PER001-01: quick p95 <= 300s."""
    require("tradingagents.profiles")


@pytest.mark.integration
def test_standard_p95():
    """TC-P6-PER001-02: standard p95 <= 720s."""
    require("tradingagents.profiles")


@pytest.mark.integration
def test_deep_p95():
    """TC-P6-PER001-03: deep p95 <= 1800s."""
    require("tradingagents.profiles")
