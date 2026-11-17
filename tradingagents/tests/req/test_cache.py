"""REQ-FR-005 — Cache (Part 4).

Traceable to test-cases/part4-resilience-pit.md. The cache subject is not
implemented yet.
"""

from tests.req._support import require


def test_hit_rate():
    """TC-P4-FR005-03: cache hit rate >= 0.70."""
    require("tradingagents.cache")


def test_no_stale():
    """TC-P4-FR005-04: no stale cache use."""
    require("tradingagents.cache")
