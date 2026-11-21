"""REQ-QUAL-002 — Report numeric faithfulness and citation support (Part 3).

Traceable to test-cases/part3-evidence-records.md. Exercises
``tradingagents.evidence.fidelity`` directly with synthetic reports and snapshots.
"""

from tradingagents.evidence.fidelity import (
    citation_support_rate,
    extract_numeric_claims,
    numeric_claim_recall,
    numeric_contradiction_rate,
    report_schema_valid,
    unsupported_claim_rate,
)

SNAPSHOT = """
### Latest verified OHLCV row
| Field | Value |
|---|---:|
| Close | 187.2 |
| Open | 185.0 |
| High | 188.0 |
| Low | 184.5 |
"""


def test_numeric():
    """TC-P3-QUAL002-01: a claim contradicting the snapshot is flagged."""
    good = "The close was 187.2 today."
    bad = "The close was 189.5 today."
    # clean report: 0 contradiction rate
    assert numeric_contradiction_rate([good], SNAPSHOT) == 0.0
    # contradictory report: rate > threshold (2%)
    rate = numeric_contradiction_rate([bad], SNAPSHOT)
    assert rate > 0.02


def test_citations():
    """TC-P3-QUAL002-02: citation support = fraction of refs that resolve."""
    known = {"tool:1", "news:2", "snap:3"}
    all_good = ["tool:1", "news:2", "snap:3"]
    mostly = ["tool:1", "news:2", "snap:3", "ghost:9"]
    assert citation_support_rate(all_good, known) == 1.0
    assert citation_support_rate(mostly, known) == 0.75


def test_unsupported():
    """TC-P3-QUAL002-03: unsupported-claim rate = claims lacking a ref."""
    claims = ["claim a", "claim b", "claim c", "claim d"]
    refs = ["r1", "r2", "r3"]  # 3 of 4 supported -> 0.25 unsupported
    assert unsupported_claim_rate(claims, refs) == 0.25
    assert unsupported_claim_rate([], []) == 0.0


def test_schema():
    """TC-P3-QUAL002-04: a report must carry the required sections."""
    good = "# Report\n\n## Rating\n\nBuy\n\n## Investment Thesis\n\nbecause"
    bad = "# Report\n\nno sections here"
    assert report_schema_valid(good) is True
    assert report_schema_valid(bad) is False


def test_extractor_recall():
    """TC-P3-QUAL002-05: extractor finds the hand-labelled numbers."""
    text = "Close 187.2, RSI 71.3, target $250, volume 1,200,000, up 3.5%."
    golden = {"187.2", "71.3", "250", "1200000", "3.5"}
    found = {c.normalized for c in extract_numeric_claims(text)}
    recall = numeric_claim_recall(text, golden)
    assert recall >= 0.95
    assert golden.issubset(found)
