"""REQ-FR-005 — Fallback / degradation (Part 4).

Traceable to test-cases/part4-resilience-pit.md. The resilience subject is not
implemented yet.
"""

from tests.req._support import require


def test_no_fabrication():
    """TC-P4-FR005-05: no fabricated data on source failure."""
    require("tradingagents.resilience")


def test_typed_events():
    """TC-P4-FR005-06: typed fallback events recorded."""
    require("tradingagents.resilience")


def test_llm_failure_degrade():
    """TC-P4-FR005-07: LLM failure retries then degrades to REVIEW."""
    require("tradingagents.resilience")
