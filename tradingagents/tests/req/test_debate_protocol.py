"""REQ-FR-003 — Structured debate protocol (Part 2).

Traceable to test-cases/part2-debate.md. The subject ``tradingagents.agents.debate``
is not implemented yet.
"""

import pytest

from tests.req._support import require

DEBATE = "tradingagents.agents.debate"


def test_schema_valid():
    """TC-P2-FR003-01: valid turns pass schema."""
    import json
    from copy import deepcopy
    from pathlib import Path

    from pydantic import ValidationError

    debate = require(DEBATE)
    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
    normal = json.loads((fixtures / "normal.json").read_text(encoding="utf-8"))
    templates = normal["transcript"]["turns"]
    previous = []
    for number in range(1, 31):
        payload = deepcopy(templates[(number - 1) % 2])
        payload.update(
            turn_id=f"schema-{number}",
            round=number,
            rebuttal_to=previous[-1].turn_id if previous else None,
        )
        before = deepcopy(payload)
        turn = debate.validate_turn(
            payload, previous, expected_speaker=payload["speaker"], expected_round=number
        )
        assert payload == before
        assert turn.round == number
        assert turn.speaker == ("bull" if number % 2 else "bear")
        previous.append(turn)
    assert len(previous) == 30

    missing = json.loads((fixtures / "missing_fields.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        debate.validate_turn(missing["turn"])
    for field, value in (
        ("speaker", "manager"),
        ("stance", "buy"),
        ("round", 0),
        ("confidence", -0.01),
        ("confidence", 1.01),
        ("evidence_refs", []),
        ("evidence_refs", [{"kind": "market", "id": "price"}]),
    ):
        payload = deepcopy(templates[0])
        payload[field] = value
        with pytest.raises((ValidationError, ValueError)):
            debate.validate_turn(payload)

    no_evidence = deepcopy(templates[0])
    no_evidence.update(evidence_refs=[], no_new_evidence=True)
    assert debate.validate_turn(no_evidence).no_new_evidence is True
    bad = json.loads((fixtures / "bad_rebuttal.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="existing earlier turn_id"):
        debate.validate_turn(bad["transcript"]["turns"][1], bad["transcript"]["turns"][:1])

    same_speaker = deepcopy(templates[0])
    same_speaker.update(turn_id="same-speaker", round=2)
    with pytest.raises(ValueError, match="speakers must alternate"):
        debate.validate_turn(same_speaker, templates[:1])
    old_round = deepcopy(templates[1])
    old_round.update(turn_id="old-round", round=1)
    with pytest.raises(ValueError, match="round must increase"):
        debate.validate_turn(old_round, templates[:1])
    duplicate_id = deepcopy(templates[1])
    duplicate_id["turn_id"] = templates[0]["turn_id"]
    with pytest.raises(ValueError, match="turn_id must be unique"):
        debate.validate_turn(duplicate_id, templates[:1])


def test_max_rounds():
    """TC-P2-FR003-02: max rounds enforced."""
    import json
    from copy import deepcopy
    from pathlib import Path
    from types import SimpleNamespace

    from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
    from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
    from tradingagents.graph.conditional_logic import ConditionalLogic

    debate = require(DEBATE)
    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
    templates = json.loads((fixtures / "normal.json").read_text(encoding="utf-8"))[
        "transcript"
    ]["turns"]
    calls = []

    def complete(prompt):
        calls.append(prompt)
        number = len(calls)
        payload = deepcopy(templates[(number - 1) % 2])
        payload.update(
            turn_id=f"turn-{number}",
            round=number,
            rebuttal_to=f"turn-{number - 1}" if number > 1 else None,
            no_new_evidence=False,
        )
        text = json.dumps(payload, ensure_ascii=False)
        return text if number % 2 else SimpleNamespace(content=text)

    llm = SimpleNamespace(invoke=complete)
    nodes = {
        "Bull Researcher": create_bull_researcher(llm),
        "Bear Researcher": create_bear_researcher(llm),
    }
    initial = {
        "company_of_interest": "TEST",
        "asset_type": "stock",
        "market_report": "示例价格证据。",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "示例估值证据。",
        "investment_debate_state": {
            "history": "", "bull_history": "", "bear_history": "",
            "current_response": "", "count": 0,
        },
    }
    state = deepcopy(initial)
    logic = ConditionalLogic(max_debate_rounds=2)
    targets = []
    for _ in range(6):
        target = logic.should_continue_debate(state)
        targets.append(target)
        if target == "Research Manager":
            break
        before = deepcopy(state)
        update = nodes[target](state)
        assert state == before
        state = {**state, **update}
        current = state["investment_debate_state"]
        prefix = "Bull Analyst:" if target == "Bull Researcher" else "Bear Analyst:"
        assert current["current_response"].startswith(prefix)
        assert current["quality_available"] is True
    assert targets == [
        "Bull Researcher", "Bear Researcher", "Bull Researcher", "Bear Researcher",
        "Research Manager",
    ]
    assert len(calls) == 4
    current = state["investment_debate_state"]
    assert current["count"] == 4
    assert [turn["round"] for turn in current["turns"]] == [1, 2, 3, 4]
    assert [turn["speaker"] for turn in current["turns"]] == ["bull", "bear", "bull", "bear"]
    assert current["bull_history"].count("Bull Analyst:") == 2
    assert current["bear_history"].count("Bear Analyst:") == 2
    assert debate.should_stop(current["turns"], 2) is True
    assert all("not available" in prompt for prompt in calls)

    legacy_calls = []

    def legacy_complete(prompt):
        legacy_calls.append(prompt)
        return SimpleNamespace(content="legacy argument")

    legacy_llm = SimpleNamespace(invoke=legacy_complete)
    legacy = deepcopy(initial)
    legacy["investment_debate_state"]["enable_structured_debate"] = False
    for factory in (create_bull_researcher, create_bear_researcher):
        before = deepcopy(legacy)
        legacy = {**legacy, **factory(legacy_llm)(legacy)}
        assert before["investment_debate_state"]["enable_structured_debate"] is False
        assert legacy["investment_debate_state"]["enable_structured_debate"] is False
        assert not legacy["investment_debate_state"].get("turns")
    assert len(legacy_calls) == 2
    assert legacy["investment_debate_state"]["current_response"] == "Bear Analyst: legacy argument"
    assert ConditionalLogic(max_debate_rounds=1).should_continue_debate(legacy) == "Research Manager"
    fallback = deepcopy(initial)
    fallback["investment_debate_state"]["count"] = 4
    assert logic.should_continue_debate(fallback) == "Research Manager"


def test_convergence_fixtures():
    """TC-P2-FR003-03: convergence decision correct on fixtures."""
    import json
    from copy import deepcopy
    from pathlib import Path

    debate = require(DEBATE)
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "debate" / "convergence.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    convergent = fixture["convergent"]
    non_convergent = fixture["non_convergent"]
    assert debate.should_stop(convergent, 3) is fixture["expected_should_stop"]["convergent"]
    assert debate.should_stop(non_convergent, 3) is fixture["expected_should_stop"]["non_convergent"]
    assert debate.should_stop(debate.DebateTranscript.model_validate(convergent), 3) is True
    for count in range(4):
        assert debate.should_stop(convergent["turns"][:count], 3) is False

    first_pair = deepcopy(convergent["turns"][:2])
    for turn in first_pair:
        turn["no_new_evidence"] = True
    assert debate.should_stop(first_pair, 3) is False
    for index in (-2, -1):
        one_side_has_evidence = deepcopy(convergent)
        one_side_has_evidence["turns"][index]["no_new_evidence"] = False
        one_side_has_evidence["turns"][index]["evidence_refs"] = ["news:new-evidence"]
        assert debate.should_stop(one_side_has_evidence, 3) is False
        changed_stance = deepcopy(convergent)
        changed_stance["turns"][index]["stance"] = "neutral"
        assert debate.should_stop(changed_stance, 3) is False

    incomplete_pair = deepcopy(convergent["turns"])
    extra_bull = deepcopy(incomplete_pair[-2])
    extra_bull.update(
        turn_id="incomplete-5", round=5, rebuttal_to=incomplete_pair[-1]["turn_id"]
    )
    incomplete_pair.append(extra_bull)
    assert debate.should_stop(incomplete_pair, 4) is False
    invalid = deepcopy(convergent)
    invalid["turns"][-1]["status"] = "invalid"
    invalid["quality_available"] = False
    assert debate.should_stop(invalid, 3) is False
    assert debate.should_stop(non_convergent, 2) is True


def test_export_schema():
    """TC-P2-FR003-04: transcript export schema valid."""
    import json
    from copy import deepcopy
    from pathlib import Path

    debate = require(DEBATE)
    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
    normal = json.loads((fixtures / "normal.json").read_text(encoding="utf-8"))["transcript"]
    unordered = deepcopy(normal)
    unordered["turns"].reverse()
    before = deepcopy(unordered)
    exported = debate.export_transcript(unordered)
    assert unordered == before
    assert exported["transcript_id"] == normal["transcript_id"]
    assert [turn["round"] for turn in exported["turns"]] == [1, 2]
    assert exported == normal
    assert debate.DebateTranscript.model_validate(json.loads(json.dumps(exported)))
    model = debate.DebateTranscript.model_validate(normal)
    assert debate.export_transcript(model) == normal
    assert model.model_dump(mode="json") == normal

    invalid = deepcopy(normal)
    invalid["turns"][-1]["status"] = "invalid"
    invalid["quality_available"] = False
    invalid_export = debate.export_transcript(invalid)
    assert invalid_export["quality_available"] is False
    assert invalid_export["turns"][-1]["status"] == "invalid"
    assert debate.DebateTranscript.model_validate(invalid_export)


def test_research_manager_preserves_structured_debate_fields():
    from types import SimpleNamespace

    from tradingagents.agents.managers.research_manager import create_research_manager

    class _LLM:
        def invoke(self, prompt):
            return SimpleNamespace(content="Recommendation: Hold\nRationale: balanced.")

    turns = [{"turn_id": "t1", "round": 1, "speaker": "bull"}]
    state = {
        "company_of_interest": "TEST",
        "asset_type": "stock",
        "investment_debate_state": {
            "history": "history",
            "bull_history": "bull",
            "bear_history": "bear",
            "current_response": "",
            "count": 1,
            "turns": turns,
            "quality_available": False,
            "enable_structured_debate": True,
        },
    }

    update = create_research_manager(_LLM())(state)
    debate = update["investment_debate_state"]

    assert debate["turns"] == turns
    assert debate["quality_available"] is False
    assert debate["enable_structured_debate"] is True


def test_retry_then_degrade():
    """TC-P2-FR003-05: invalid turn retries once then degrades."""
    import json
    from copy import deepcopy
    from pathlib import Path
    from types import SimpleNamespace

    from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
    from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
    from tradingagents.graph.conditional_logic import ConditionalLogic

    debate = require(DEBATE)
    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
    valid = json.loads((fixtures / "normal.json").read_text(encoding="utf-8"))[
        "transcript"
    ]["turns"][0]
    missing = json.loads((fixtures / "missing_fields.json").read_text(encoding="utf-8"))["turn"]
    valid_text = json.dumps(valid, ensure_ascii=False)
    state = {
        "company_of_interest": "TEST",
        "investment_debate_state": {
            "history": "existing history", "bull_history": "", "bear_history": "",
            "current_response": "", "count": 0, "turns": [], "quality_available": True,
        },
    }

    def exercise(responses):
        calls = []

        def complete(prompt):
            calls.append(prompt)
            response = responses[len(calls) - 1]
            if isinstance(response, Exception):
                raise response
            return response

        before = deepcopy(state)
        turn = debate.run_debate_turn(state, "bull", complete)
        assert state == before
        assert len(calls) <= 2
        return turn, calls

    for response in (valid_text, SimpleNamespace(content=valid_text), {"content": valid_text}):
        turn, calls = exercise([response])
        assert turn.status == "ok"
        assert turn.claim == valid["claim"]
        assert len(calls) == 1
        assert "has not spoken yet" in calls[0]

    for response in ("not json", json.dumps(missing), "[]", RuntimeError("synthetic failure")):
        turn, calls = exercise([response, SimpleNamespace(content=valid_text)])
        assert turn.status == "ok"
        assert len(calls) == 2
        assert calls[1].startswith(calls[0])

    wrong_speaker = deepcopy(valid)
    wrong_speaker["speaker"] = "bear"
    wrong_round = deepcopy(valid)
    wrong_round["round"] = 2
    invalid_status = deepcopy(valid)
    invalid_status["status"] = "invalid"
    for response in (
        "{",
        "[]",
        json.dumps(missing),
        json.dumps(wrong_speaker),
        json.dumps(wrong_round),
        json.dumps(invalid_status),
        SimpleNamespace(content=None),
        RuntimeError("synthetic failure"),
    ):
        turn, calls = exercise([response, response])
        assert len(calls) == 2
        assert turn.status == "invalid"
        assert turn.no_new_evidence is True
        assert turn.evidence_refs == []
        assert turn.speaker == "bull"
        assert turn.round == 1
        assert set(turn.model_dump()) == set(valid)
        assert debate.validate_turn(turn).status == "invalid"

    for factory, prefix in (
        (create_bull_researcher, "Bull Analyst:"),
        (create_bear_researcher, "Bear Analyst:"),
    ):
        calls = []

        def invalid_complete(prompt, calls=calls):
            calls.append(prompt)
            return SimpleNamespace(content="not json")

        before = deepcopy(state)
        update = factory(SimpleNamespace(invoke=invalid_complete))(state)
        assert state == before
        current = update["investment_debate_state"]
        assert len(calls) == 2
        assert current["turns"][-1]["status"] == "invalid"
        assert current["quality_available"] is False
        assert current["current_response"].startswith(prefix)
        assert current["history"].startswith("existing history")
        assert ConditionalLogic(max_debate_rounds=2).should_continue_debate(
            {**state, **update}
        ) == "Research Manager"

    unavailable = deepcopy(state)
    unavailable["investment_debate_state"]["quality_available"] = False
    update = create_bull_researcher(
        SimpleNamespace(invoke=lambda prompt: valid_text)
    )(unavailable)
    assert update["investment_debate_state"]["turns"][-1]["status"] == "ok"
    assert update["investment_debate_state"]["quality_available"] is False


@pytest.mark.integration
def test_live_schema_valid():
    """TC-P2-FR003-06: 30 live runs schema-valid (integration)."""
    require(DEBATE)
