"""REQ-FR-004 — Evidence refs and run manifest (Part 3).

Traceable to test-cases/part3-evidence-records.md. The evidence/manifest artifacts
are not implemented yet; these tests skip until they land.
"""

from tests.req._support import require

EVIDENCE = "tradingagents.evidence"
CONTRACTS = "tradingagents.contracts"


def test_numeric_refs():
    """TC-P3-FR004-01: numeric claims carry evidence refs."""
    require(EVIDENCE)


def test_qualitative_refs():
    """TC-P3-FR004-02: qualitative claims mostly carry refs."""
    require(EVIDENCE)


def test_manifest_schema():
    """TC-P3-FR004-03: manifest validates against schema."""
    require(CONTRACTS)


def test_token_sum():
    """TC-P3-FR004-04: manifest token sum matches events."""
    require(CONTRACTS)


def test_replay():
    """TC-P3-FR004-05: manifest replays to the same rating."""
    require(CONTRACTS)


def test_orphan_number_must_fail():
    """TC-P3-FR004-06: an unreferenced number is flagged."""
    require(EVIDENCE)
