"""REQ-QUAL-001 — Debate quality proxy metrics (Part 2).

Traceable to test-cases/part2-debate.md. The subject ``tradingagents.agents.debate``
(its ``quality`` module) is not implemented yet.
"""

import pytest

from tests.req._support import require

DEBATE = "tradingagents.agents.debate"


def test_evidence_coverage():
    """TC-P2-QUAL001-01: evidence coverage per turn."""
    require(DEBATE)


def test_rebuttal_coverage():
    """TC-P2-QUAL001-02: rebuttal coverage >= 0.90."""
    require(DEBATE)


def test_unsupported_claim_rate():
    """TC-P2-QUAL001-03: unsupported-claim rate <= 0.05."""
    require(DEBATE)


def test_duplicate_claim_rate():
    """TC-P2-QUAL001-04: duplicate-claim rate <= 0.10."""
    require(DEBATE)


@pytest.mark.integration
def test_quality_golden_determinism():
    """TC-P2-QUAL001-05: metrics match golden values (golden fixtures)."""
    require(DEBATE)


@pytest.mark.integration
def test_live_metrics():
    """TC-P2-QUAL001-06: metrics over 30 real transcripts (integration)."""
    require(DEBATE)
