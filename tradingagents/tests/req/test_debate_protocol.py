"""REQ-FR-003 — Structured debate protocol (Part 2).

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
