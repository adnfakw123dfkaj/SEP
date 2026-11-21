"""Claim-level report evidence groups."""

import pytest

from tradingagents.agents import tools
from tradingagents.evidence import evidence_scope
from tradingagents.evidence.claims import (
    build_report_claims,
    claim_evidence_metrics,
    numeric_claim_contradiction,
)

pytestmark = pytest.mark.unit


def _state():
    return {
        "market_report": "The close was 125.53 on heavy volume.",
        "final_trade_decision": (
            "**Rating**: Underweight\n\n**Investment Thesis**: reduce exposure."
        ),
        "evidence": [
            {
                "kind": "tool",
                "id": "tool-market",
                "source": "get_stock_data:yfinance",
                "snapshot_hash": "hash-market",
            },
            {
                "kind": "tool",
                "id": "tool-news",
                "source": "get_news:yfinance",
                "snapshot_hash": "hash-news",
            },
        ],
    }


def test_report_claims_attach_section_evidence_and_snapshot_hashes():
    claims = build_report_claims(_state())

    market = next(claim for claim in claims if claim["section"] == "market")
    decision = next(claim for claim in claims if claim["section"] == "decision")
    assert market["kind"] == "numeric"
    assert market["evidence_refs"] == ["tool-market"]
    assert market["snapshot_hashes"] == ["hash-market"]
    assert decision["kind"] == "qualitative"
    assert set(decision["evidence_refs"]) == {"tool-market", "tool-news"}
    assert decision["claim_id"].startswith("decision-")


def test_claim_metrics_count_numeric_and_qualitative_support():
    metrics = claim_evidence_metrics(build_report_claims(_state()))

    assert metrics["claim_count"] == 3
    assert metrics["numeric_claim_evidence_rate"] == 1.0
    assert metrics["qualitative_claim_evidence_rate"] == 1.0
    assert metrics["claim_unsupported_rate"] == 0.0


def test_claim_metrics_detect_unsupported_numeric_claims():
    state = _state()
    state["evidence"] = [state["evidence"][1]]

    metrics = claim_evidence_metrics(build_report_claims(state))

    assert metrics["numeric_claim_evidence_rate"] == 0.0
    assert metrics["claim_unsupported_rate"] > 0.0


def test_numeric_contradiction_checks_labelled_values_only():
    claims = [
        {
            "claim_id": "market-0001",
            "kind": "numeric",
            "text": "The close was 187.2, RSI 71.3, down 5% from the peak.",
        },
        {
            "claim_id": "market-0002",
            "kind": "numeric",
            "text": "The close was 189.5.",
        },
        {
            "claim_id": "decision-0001",
            "kind": "qualitative",
            "text": "ignore this one",
        },
    ]
    snapshot = "| Close | 187.2 |\n| rsi | 71.3 |"

    result = numeric_claim_contradiction(claims, snapshot)

    assert result["checked"] == 3
    assert result["contradictions"] == 1
    assert result["rate"] == pytest.approx(1 / 3)
    assert result["details"][0]["claim_id"] == "market-0002"


def test_numeric_contradiction_skips_the_date_before_a_close():
    claims = [
        {
            "claim_id": "decision-0001",
            "section": "decision",
            "kind": "numeric",
            "text": "NVDA closed 2026-11-20 at 125.53.",
        }
    ]

    result = numeric_claim_contradiction(
        claims,
        "| Close | 125.53 |",
        sections={"decision"},
    )

    assert result["checked"] == 1
    assert result["rate"] == 0.0


def test_numeric_contradiction_ignores_cycle_lows_but_checks_session_lows():
    claims = [
        {
            "claim_id": "decision-0001",
            "section": "decision",
            "kind": "numeric",
            "text": "MACD is at a window low of -19.83; the session low was 124.50.",
        }
    ]

    result = numeric_claim_contradiction(
        claims,
        "| Low | 124.50 |",
        sections={"decision"},
    )

    assert result["checked"] == 1
    assert result["contradictions"] == 0


def test_numeric_contradiction_ignores_percentages_and_unlabelled_numbers():
    claims = [
        {
            "claim_id": "decision-0001",
            "kind": "numeric",
            "text": "Target 120 after a 14% decline.",
        }
    ]

    result = numeric_claim_contradiction(claims, "| Close | 187.2 |")

    assert result["checked"] == 0
    assert result["rate"] is None


def test_verified_snapshot_tool_registers_text_and_evidence(monkeypatch):
    monkeypatch.setattr(
        tools,
        "build_verified_market_snapshot",
        lambda *args, **kwargs: "| Close | 125.53 |",
    )

    with evidence_scope() as registry:
        result = tools.get_verified_market_snapshot.func(
            "NVDA", "2026-11-20", 30, ""
        )

    assert result == "| Close | 125.53 |"
    assert registry.snapshot_text() == result
    assert any(ref.source.startswith("get_verified_market_snapshot") for ref in registry.all())
