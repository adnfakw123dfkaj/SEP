"""REQ-FR-004 / REQ-QUAL-002 — Evidence, report, manifest (Part 3).

Traceable to test-cases/part3-evidence-records.md. The evidence/manifest/report
artifacts are not implemented yet; these tests skip until they land.
"""

from tests.req._support import require

EVIDENCE = "tradingagents.evidence"
CONTRACTS = "tradingagents.contracts"


# REQ-FR-004 — evidence refs + manifest
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


# REQ-QUAL-002 — report faithfulness
def test_numeric_contradiction():
    """TC-P3-QUAL002-01: contradiction vs snapshot <= 2%."""
    require(EVIDENCE)


def test_citation_support():
    """TC-P3-QUAL002-02: citation support >= 0.95."""
    require(EVIDENCE)


def test_unsupported_rate():
    """TC-P3-QUAL002-03: unsupported-claim rate <= 0.05."""
    require(EVIDENCE)


def test_report_schema():
    """TC-P3-QUAL002-04: report schema valid."""
    require(EVIDENCE)


def test_extractor_recall():
    """TC-P3-QUAL002-05: extractor recall >= 0.95."""
    require(EVIDENCE)


def test_snapshot_contradiction_must_fail():
    """TC-P3-QUAL002-06: a snapshot contradiction is flagged."""
    require(EVIDENCE)
