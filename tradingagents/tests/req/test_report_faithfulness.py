"""REQ-QUAL-002 — Report numeric faithfulness and citation support (Part 3).

Traceable to test-cases/part3-evidence-records.md. The fidelity subject
(``tradingagents.evidence.fidelity``) is not implemented yet.
"""

from tests.req._support import require

EVIDENCE = "tradingagents.evidence"


def test_numeric():
    """TC-P3-QUAL002-01: contradiction vs snapshot <= 2%."""
    require(EVIDENCE)


def test_citations():
    """TC-P3-QUAL002-02: citation support >= 0.95."""
    require(EVIDENCE)


def test_unsupported():
    """TC-P3-QUAL002-03: unsupported-claim rate <= 0.05."""
    require(EVIDENCE)


def test_schema():
    """TC-P3-QUAL002-04: report schema valid."""
    require(EVIDENCE)


def test_extractor_recall():
    """TC-P3-QUAL002-05: extractor recall >= 0.95."""
    require(EVIDENCE)
