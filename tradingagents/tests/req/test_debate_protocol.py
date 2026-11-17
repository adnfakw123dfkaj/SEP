"""REQ-FR-003 / REQ-QUAL-001 — Structured debate and quality (Part 2).

Traceable to test-cases/part2-debate.md. The subject ``tradingagents.agents.debate``
is not implemented yet.
"""

import pytest

from tests.req._support import require

DEBATE = "tradingagents.agents.debate"


def test_schema_valid():
    """TC-P2-FR003-01: valid turns pass schema."""
    require(DEBATE)


def test_max_rounds():
    """TC-P2-FR003-02: max rounds enforced."""
    require(DEBATE)


def test_convergence_fixtures():
    """TC-P2-FR003-03: convergence decision correct on fixtures."""
    require(DEBATE)


def test_export_schema():
    """TC-P2-FR003-04: transcript export schema valid."""
    require(DEBATE)


def test_retry_then_degrade():
    """TC-P2-FR003-05: invalid turn retries once then degrades."""
    require(DEBATE)


@pytest.mark.integration
def test_live_schema_valid():
    """TC-P2-FR003-06: 30 live runs schema-valid (integration)."""
    require(DEBATE)


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


def test_quality_golden_determinism():
    """TC-P2-QUAL001-05: metrics match golden values."""
    require(DEBATE)


@pytest.mark.integration
def test_live_metrics():
    """TC-P2-QUAL001-06: metrics over 30 real transcripts (integration)."""
    require(DEBATE)
