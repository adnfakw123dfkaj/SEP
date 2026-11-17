"""REQ-FR-005 — Checkpoint resume (Part 4).

Traceable to test-cases/part4-resilience-pit.md. The cache/resilience wrappers are
not implemented yet; the underlying per-ticker checkpointer exists but the
node-level resume-reuse / no-duplicate-call guarantees are added by the Part 4
work, so these skip until then.
"""

from tests.req._support import require


def test_resume_reuse():
    """TC-P4-FR005-01: resume reuses completed nodes."""
    require("tradingagents.cache")


def test_no_duplicate_calls():
    """TC-P4-FR005-02: no duplicate LLM calls on resume."""
    require("tradingagents.cache")
