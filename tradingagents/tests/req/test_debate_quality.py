"""REQ-QUAL-001 — Debate quality proxy metrics (Part 2).

Traceable to test-cases/part2-debate.md. The subject ``tradingagents.agents.debate``
(its ``quality`` module) is not implemented yet.
"""

import pytest

from tests.req._support import require

DEBATE = "tradingagents.agents.debate"


def test_evidence_coverage():
    """TC-P2-QUAL001-01: evidence coverage per turn."""
    import json
    from copy import deepcopy
    from pathlib import Path

    from tradingagents.agents.debate import (
        DebateTranscript,
        QualityMetrics,
        score_debate,
    )

    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
    normal = json.loads((fixtures / "normal.json").read_text(encoding="utf-8"))[
        "transcript"
    ]
    original = deepcopy(normal)
    metrics = score_debate(normal)
    assert isinstance(metrics, QualityMetrics)
    assert metrics.quality_available is True
    assert metrics.turns_with_evidence_or_no_new_evidence_rate == 1.0
    assert metrics.rebuttal_coverage == 1.0
    assert metrics.unsupported_claim_rate == 0.0
    assert metrics.duplicate_claim_rate == 0.0
    assert normal == original

    model = DebateTranscript.model_validate(normal)
    before = model.model_dump()
    assert score_debate(model) == metrics
    assert model.model_dump() == before
    model_turns = {**normal, "turns": model.turns}
    assert score_debate(model_turns) == metrics

    convergence = json.loads(
        (fixtures / "convergence.json").read_text(encoding="utf-8")
    )["convergent"]
    converged_metrics = score_debate(convergence)
    assert converged_metrics.quality_available is True
    assert converged_metrics.turns_with_evidence_or_no_new_evidence_rate == 1.0
    assert converged_metrics.unsupported_claim_rate == 0.5

    uncovered = deepcopy(normal)
    uncovered["turns"][0]["evidence_refs"] = []
    uncovered["turns"][0]["no_new_evidence"] = False
    uncovered_before = deepcopy(uncovered)
    uncovered_metrics = score_debate(uncovered)
    assert uncovered_metrics.quality_available is True
    assert uncovered_metrics.turns_with_evidence_or_no_new_evidence_rate == 0.5
    assert uncovered_metrics.turns_with_evidence_or_no_new_evidence_rate != 1.0
    assert uncovered == uncovered_before

    invalid = deepcopy(normal)
    invalid["turns"][-1]["status"] = "invalid"
    unavailable_cases = [
        {"turns": [], "quality_available": True},
        {**normal, "quality_available": False},
        {"turns": normal["turns"]},
        invalid,
    ]
    for transcript in unavailable_cases:
        before = deepcopy(transcript)
        unavailable = score_debate(transcript)
        assert unavailable.quality_available is False
        assert unavailable.turns_with_evidence_or_no_new_evidence_rate is None
        assert unavailable.rebuttal_coverage is None
        assert unavailable.unsupported_claim_rate is None
        assert unavailable.duplicate_claim_rate is None
        assert transcript == before

    invalid_model = DebateTranscript.model_validate(
        {**invalid, "quality_available": False}
    )
    assert score_debate(invalid_model) == QualityMetrics()
    empty_model = DebateTranscript.model_validate(
        {"transcript_id": "empty", "turns": [], "quality_available": True}
    )
    assert score_debate(empty_model) == QualityMetrics()


def test_rebuttal_coverage():
    """TC-P2-QUAL001-02: rebuttal coverage >= 0.90."""
    import json
    from copy import deepcopy
    from pathlib import Path

    from tradingagents.agents.debate import score_debate

    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
    normal = json.loads((fixtures / "normal.json").read_text(encoding="utf-8"))[
        "transcript"
    ]

    def make_transcript(valid_rebuttals):
        turns = []
        # 一条开场 + 30 条可反驳发言，首条不进入反驳覆盖率的分母。
        for index in range(31):
            turn = deepcopy(normal["turns"][index % 2])
            turn.update(
                turn_id=f"coverage-{index}",
                round=index // 2 + 1,
                rebuttal_to=(
                    None
                    if index == 0
                    else (
                        f"coverage-{index - 1}"
                        if index <= valid_rebuttals
                        else "missing-turn"
                    )
                ),
            )
            turns.append(turn)
        return {"turns": turns, "quality_available": True}

    passing = make_transcript(27)
    before = deepcopy(passing)
    metrics = score_debate(passing)
    assert metrics.quality_available is True
    assert len(passing["turns"]) - 1 == 30
    assert metrics.rebuttal_coverage == pytest.approx(27 / 30)
    assert metrics.rebuttal_coverage >= 0.90
    assert passing == before
    failing = score_debate(make_transcript(26))
    assert failing.quality_available is True
    assert failing.rebuttal_coverage == pytest.approx(26 / 30)
    assert failing.rebuttal_coverage < 0.90

    bad = json.loads((fixtures / "bad_rebuttal.json").read_text(encoding="utf-8"))[
        "transcript"
    ]
    assert score_debate(bad).rebuttal_coverage == 0.0
    for target in (None, "normal-2", "future-turn"):
        bad = deepcopy(normal)
        bad["turns"][1]["rebuttal_to"] = target
        assert score_debate(bad).rebuttal_coverage == 0.0

    future = make_transcript(30)
    future["turns"][1]["rebuttal_to"] = future["turns"][2]["turn_id"]
    assert score_debate(future).rebuttal_coverage == pytest.approx(29 / 30)
    opening = {**normal, "turns": normal["turns"][:1]}
    assert score_debate(opening).rebuttal_coverage == 1.0


def test_unsupported_claim_rate():
    """TC-P2-QUAL001-03: unsupported-claim rate <= 0.05."""
    import json
    from copy import deepcopy
    from pathlib import Path

    from tradingagents.agents.debate import score_debate

    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
    normal = json.loads((fixtures / "normal.json").read_text(encoding="utf-8"))[
        "transcript"
    ]

    def make_transcript(unsupported_count):
        turns = []
        for index in range(40):
            turn = deepcopy(normal["turns"][index % 2])
            turn.update(
                turn_id=f"unsupported-{index}",
                round=index // 2 + 1,
                rebuttal_to=f"unsupported-{index - 1}" if index else None,
            )
            if index < unsupported_count:
                turn["evidence_refs"] = []
                turn["no_new_evidence"] = True
            turns.append(turn)
        return {"turns": turns, "quality_available": True}

    for count, expected_pass in ((2, True), (3, False)):
        transcript = make_transcript(count)
        before = deepcopy(transcript)
        metrics = score_debate(transcript)
        assert metrics.quality_available is True
        assert metrics.turns_with_evidence_or_no_new_evidence_rate == 1.0
        assert metrics.unsupported_claim_rate == pytest.approx(count / 40)
        assert (metrics.unsupported_claim_rate <= 0.05) is expected_pass
        assert transcript == before


def test_duplicate_claim_rate():
    """TC-P2-QUAL001-04: duplicate-claim rate <= 0.10."""
    import json
    from copy import deepcopy
    from pathlib import Path

    from tradingagents.agents.debate import score_debate

    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
    golden = json.loads(
        (fixtures / "duplicate_claims.json").read_text(encoding="utf-8")
    )["transcript"]
    original = deepcopy(golden)
    assert score_debate(golden).duplicate_claim_rate == pytest.approx(1 / 3)
    assert golden == original

    distinct_claims = [
        "Revenue growth is supported by rising subscription demand.",
        "Foreign currency volatility may reduce overseas earnings.",
        "A new warehouse will shorten regional delivery times.",
        "Patent protection expires before the next product launch.",
        "Lower copper prices improve manufacturing margins.",
        "Customer retention has weakened among small businesses.",
        "Regulatory review could delay the planned acquisition.",
        "Cash reserves can fund several years of operations.",
        "An aging fleet requires substantial maintenance spending.",
        "Cloud migration reduces the need for physical servers.",
        "The board approved a quarterly dividend increase.",
        "Competitor discounts put pressure on premium pricing.",
        "Higher interest rates increase refinancing expenses.",
        "A diversified supplier network limits disruption risk.",
        "Store closures remove unprofitable retail locations.",
        "Early clinical results suggest promising treatment efficacy.",
        "Inventory obsolescence could require a large write down.",
        "Long term energy contracts stabilize utility costs.",
        "Employee turnover threatens specialized engineering capacity.",
        "Insurance claims rose following severe coastal storms.",
        "Tourism recovery strengthens hotel occupancy.",
        "Freight congestion extends component lead times.",
        "A favorable court ruling removes a legal liability.",
        "Advertising conversion improved after the website redesign.",
        "Water shortages constrain agricultural production.",
        "Government incentives support battery factory expansion.",
        "Mobile payment adoption creates a distribution opportunity.",
    ]
    repeated_claims = [
        "  REVENUE GROWTH IS SUPPORTED BY RISING SUBSCRIPTION DEMAND!!! ",
        "revenue,, growth  is\nsupported by rising subscription demand...",
        "\tRevenue growth is supported by rising subscription demand。！？",
        "Revenue growth is supported by rising subscription demand.",
    ]

    def make_transcript(duplicate_count):
        claims = distinct_claims[:30 - duplicate_count]
        claims = claims + repeated_claims[:duplicate_count]
        turns = []
        for index, claim in enumerate(claims):
            turn = deepcopy(golden["turns"][index % 2])
            turn.update(
                turn_id=f"duplicate-{index}",
                round=index // 2 + 1,
                claim=claim,
                rebuttal_to=f"duplicate-{index - 1}" if index else None,
            )
            turns.append(turn)
        return {"turns": turns, "quality_available": True}

    for count, expected_pass in ((3, True), (4, False)):
        transcript = make_transcript(count)
        before = deepcopy(transcript)
        assert len(transcript["turns"]) == 30
        metrics = score_debate(transcript)
        assert metrics.quality_available is True
        assert metrics.duplicate_claim_rate == pytest.approx(count / 30)
        assert (metrics.duplicate_claim_rate <= 0.10) is expected_pass
        assert all(score_debate(transcript) == metrics for _ in range(3))
        assert transcript == before

    casefolded = deepcopy(golden)
    casefolded["turns"] = casefolded["turns"][:2]
    casefolded["turns"][0]["claim"] = "Straße Umsatz wächst."
    casefolded["turns"][1]["claim"] = " STRASSE,, UMSATZ\tWÄCHST!!! "
    assert score_debate(casefolded).duplicate_claim_rate == 0.5

    near_duplicate = deepcopy(golden)
    near_duplicate["turns"] = near_duplicate["turns"][:2]
    near_duplicate["turns"][0]["claim"] = distinct_claims[0]
    near_duplicate["turns"][1]["claim"] = distinct_claims[0].replace(
        "demand", "demands"
    )
    assert score_debate(near_duplicate).duplicate_claim_rate == 0.5


@pytest.mark.integration
def test_quality_golden_determinism():
    """TC-P2-QUAL001-05: metrics match golden values (golden fixtures)."""
    require(DEBATE)


@pytest.mark.integration
def test_live_metrics():
    """TC-P2-QUAL001-06: metrics over 30 real transcripts (integration)."""
    require(DEBATE)
