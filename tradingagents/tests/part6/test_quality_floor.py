"""Composite Part 2 + Part 3 + Part 5 quality floor."""

import pytest

from tradingagents.cost.quality_floor import evaluate_quality_floor

pytestmark = pytest.mark.unit

TURN = {
    "turn_id": "bull-1",
    "round": 1,
    "speaker": "bull",
    "claim": "NVDA has durable demand.",
    "evidence_refs": ["tool-1"],
    "assumptions": [],
    "rebuttal_to": None,
    "confidence": 0.6,
    "open_questions": [],
    "requested_evidence": [],
    "no_new_evidence": False,
    "status": "ok",
}

GOOD = {
    "debate_transcript": {"turns": [TURN], "quality_available": True},
    "evidence_refs": ["tool-1"],
    "evidence": [{"kind": "tool", "id": "tool-1", "source": "get_stock_data:yfinance"}],
    "report_claims": [
        {
            "claim_id": "decision-0001",
            "section": "decision",
            "kind": "numeric",
            "text": "The close was 125.53 and the target is 120.",
            "evidence_refs": ["tool-1"],
            "snapshot_hashes": ["abc"],
        }
    ],
    "final_trade_decision": (
        "**Rating**: Overweight\n\n**Investment Thesis**: demand remains strong."
    ),
    "verified_snapshot": "| Close | 125.53 |\n| RSI | 15.05 |",
    "output_validation": {"ok": True, "errors": []},
    "rating_authority": {"rating": "Overweight", "review_required": False},
}


def test_quality_floor_passes_when_all_parts_pass():
    result = evaluate_quality_floor(GOOD)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["components"]["citation_support_rate"] == 1.0


def test_quality_floor_fails_without_debate_quality():
    state = dict(GOOD, debate_transcript={"turns": [], "quality_available": True})

    result = evaluate_quality_floor(state)

    assert result["passed"] is False
    assert "debate_quality_unavailable" in result["failures"]


def test_quality_floor_fails_on_weak_rebuttal_coverage():
    second = dict(TURN, turn_id="bear-2", round=2, speaker="bear", rebuttal_to=None)
    state = dict(
        GOOD,
        debate_transcript={"turns": [TURN, second], "quality_available": True},
    )

    result = evaluate_quality_floor(state)

    assert "debate_rebuttal_coverage" in result["failures"]


def test_quality_floor_fails_on_invalid_report_schema():
    state = dict(GOOD, final_trade_decision="No required sections.")

    result = evaluate_quality_floor(state)

    assert "report_schema_invalid" in result["failures"]


def test_quality_floor_fails_without_evidence():
    state = dict(GOOD, evidence_refs=[], evidence=[])

    result = evaluate_quality_floor(state)

    assert "report_evidence_missing" in result["failures"]


def test_quality_floor_fails_on_unsupported_citations():
    state = dict(GOOD, evidence=[])

    result = evaluate_quality_floor(state)

    assert "report_citation_support" in result["failures"]


def test_quality_floor_fails_without_claim_evidence():
    state = dict(GOOD, report_claims=[])

    result = evaluate_quality_floor(state)

    assert "report_claims_missing" in result["failures"]


def test_quality_floor_fails_on_unsupported_numeric_claims():
    state = dict(
        GOOD,
        report_claims=[
            {
                "claim_id": "decision-0001",
                "section": "decision",
                "kind": "numeric",
                "text": "The close was 125.53.",
                "evidence_refs": [],
                "snapshot_hashes": [],
            }
        ],
    )

    result = evaluate_quality_floor(state)

    assert "report_numeric_claim_evidence" in result["failures"]


def test_quality_floor_fails_on_numeric_contradiction():
    state = dict(
        GOOD,
        report_claims=[
            {
                "claim_id": "decision-0001",
                "section": "decision",
                "kind": "numeric",
                "text": "The close was 999.0.",
                "evidence_refs": ["tool-1"],
                "snapshot_hashes": ["abc"],
            }
        ],
    )

    result = evaluate_quality_floor(state)

    assert "report_numeric_contradiction" in result["failures"]


def test_quality_floor_fails_when_numeric_claims_are_unchecked():
    state = dict(GOOD, verified_snapshot="")

    result = evaluate_quality_floor(state)

    assert "report_numeric_claims_unchecked" in result["failures"]


def test_quality_floor_fails_on_output_validation_and_authority():
    state = dict(
        GOOD,
        output_validation={"ok": False, "errors": ["bad"]},
        rating_authority={"rating": "REVIEW", "review_required": True},
    )

    result = evaluate_quality_floor(state)

    assert "output_validation" in result["failures"]
    assert "rating_authority" in result["failures"]
