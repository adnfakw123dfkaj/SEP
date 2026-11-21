"""Part 2 第 1 周契约测试；只读取规定目录内的固定样本。"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import tradingagents.agents.debate as debate_package
from tradingagents.agents.debate import schemas
from tradingagents.agents.debate.prompts import BEAR_PROMPT, BULL_PROMPT
from tradingagents.agents.debate.stubs import sanitize
from tradingagents.contracts.debate import DebateTranscript, DebateTurn, Stance

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "debate"
CORE_FIELDS = (
    "turn_id",
    "round",
    "speaker",
    "claim",
    "stance",
    "evidence_refs",
    "assumptions",
    "rebuttal_to",
    "confidence",
    "open_questions",
    "requested_evidence",
)


def _load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def turn_payload():
    return _load_fixture("normal.json")["transcript"]["turns"][0]


def test_normal_fixture_validates_and_roundtrips():
    payload = _load_fixture("normal.json")["transcript"]
    transcript = DebateTranscript.model_validate(payload)

    assert transcript.model_dump(mode="json") == payload
    assert DebateTranscript.model_validate_json(transcript.model_dump_json()) == transcript
    assert transcript.turns[0].rebuttal_to is None
    assert transcript.turns[1].rebuttal_to == transcript.turns[0].turn_id


def test_declared_fields_and_defaults(turn_payload):
    turn_payload.pop("no_new_evidence")
    turn_payload.pop("status")
    turn = DebateTurn.model_validate(turn_payload)

    assert set(DebateTurn.model_fields) == set(CORE_FIELDS) | {"no_new_evidence", "status"}
    assert set(DebateTranscript.model_fields) == {
        "transcript_id", "turns", "quality_available",
    }
    assert turn.no_new_evidence is False
    assert turn.status == "ok"
    assert turn.stance is Stance.BULLISH


@pytest.mark.parametrize("field", CORE_FIELDS)
def test_each_core_field_is_required(turn_payload, field):
    turn_payload.pop(field)

    with pytest.raises(ValidationError) as caught:
        DebateTurn.model_validate(turn_payload)

    assert any(error["loc"] == (field,) and error["type"] == "missing"
               for error in caught.value.errors())


@pytest.mark.parametrize("stance", ["bullish", "bearish", "neutral"])
def test_allowed_stances_serialize_as_strings(turn_payload, stance):
    turn_payload["stance"] = stance

    assert DebateTurn.model_validate(turn_payload).model_dump(mode="json")["stance"] == stance


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("speaker", "manager"),
        ("speaker", "Bull"),
        ("stance", "buy"),
        ("stance", "BULLISH"),
        ("status", "pending"),
    ],
)
def test_invalid_enum_values_are_rejected(turn_payload, field, value):
    turn_payload[field] = value

    with pytest.raises(ValidationError):
        DebateTurn.model_validate(turn_payload)


@pytest.mark.parametrize("confidence", [0, 1])
def test_confidence_boundaries_are_inclusive(turn_payload, confidence):
    turn_payload["confidence"] = confidence

    assert DebateTurn.model_validate(turn_payload).confidence == confidence


@pytest.mark.parametrize(
    "confidence",
    [-0.01, 1.01, float("nan"), float("inf"), "0.7", True],
    ids=["negative", "above_one", "nan", "infinity", "text", "boolean"],
)
def test_invalid_confidence_is_rejected(turn_payload, confidence):
    turn_payload["confidence"] = confidence

    with pytest.raises(ValidationError):
        DebateTurn.model_validate(turn_payload)


@pytest.mark.parametrize("round_value", [0, -1, True, "1"])
def test_round_is_a_positive_integer(turn_payload, round_value):
    turn_payload["round"] = round_value

    with pytest.raises(ValidationError):
        DebateTurn.model_validate(turn_payload)


@pytest.mark.parametrize(
    "refs",
    [[{"kind": "market", "id": "price"}], [123], [None], [""], ["   "]],
    ids=["object", "number", "null", "empty", "blank"],
)
def test_evidence_refs_are_nonblank_strings(turn_payload, refs):
    turn_payload["evidence_refs"] = refs

    with pytest.raises(ValidationError):
        DebateTurn.model_validate(turn_payload)


def test_missing_evidence_requires_explicit_no_new_evidence(turn_payload):
    turn_payload["evidence_refs"] = []

    with pytest.raises(ValidationError, match="no_new_evidence"):
        DebateTurn.model_validate(turn_payload)

    turn_payload["no_new_evidence"] = True
    turn = DebateTurn.model_validate(turn_payload)
    assert turn.evidence_refs == []
    assert turn.no_new_evidence is True


@pytest.mark.parametrize("value", ["false", 1])
def test_no_new_evidence_requires_a_boolean(turn_payload, value):
    turn_payload["no_new_evidence"] = value

    with pytest.raises(ValidationError):
        DebateTurn.model_validate(turn_payload)


def test_missing_fields_fixture_reports_the_missing_fields():
    fixture = _load_fixture("missing_fields.json")

    with pytest.raises(ValidationError) as caught:
        DebateTurn.model_validate(fixture["turn"])

    missing = {error["loc"][0] for error in caught.value.errors()
               if error["type"] == "missing"}
    assert missing == set(fixture["expected_missing_fields"])


def test_missing_rebuttal_fixture_is_rejected():
    payload = _load_fixture("bad_rebuttal.json")["transcript"]

    with pytest.raises(ValidationError, match="existing earlier turn_id"):
        DebateTranscript.model_validate(payload)


@pytest.mark.parametrize(
    ("turn_index", "target"),
    [(0, "normal-1"), (0, "normal-2"), (1, "normal-2")],
    ids=["opening_self_reference", "future_reference", "reply_self_reference"],
)
def test_rebuttal_cannot_reference_self_or_a_future_turn(turn_index, target):
    payload = _load_fixture("normal.json")["transcript"]
    payload["turns"][turn_index]["rebuttal_to"] = target

    with pytest.raises(ValidationError, match="existing earlier turn_id"):
        DebateTranscript.model_validate(payload)


def test_duplicate_turn_ids_are_rejected():
    payload = _load_fixture("normal.json")["transcript"]
    payload["turns"][1]["turn_id"] = payload["turns"][0]["turn_id"]

    with pytest.raises(ValidationError, match="turn_id must be unique"):
        DebateTranscript.model_validate(payload)


def test_duplicate_claim_fixture_is_valid_data_for_later_quality_checks():
    fixture = _load_fixture("duplicate_claims.json")
    transcript = DebateTranscript.model_validate(fixture["transcript"])
    by_id = {turn.turn_id: turn for turn in transcript.turns}

    for earlier, repeated in fixture["expected_duplicate_pairs"]:
        assert earlier != repeated
        assert by_id[earlier].claim == by_id[repeated].claim


def test_convergence_fixture_contains_both_contract_valid_scenarios():
    fixture = _load_fixture("convergence.json")
    convergent = DebateTranscript.model_validate(fixture["convergent"])
    non_convergent = DebateTranscript.model_validate(fixture["non_convergent"])

    assert fixture["expected_should_stop"] == {
        "convergent": True, "non_convergent": False,
    }
    assert all(turn.no_new_evidence for turn in convergent.turns[-2:])
    previous_stances = {turn.speaker: turn.stance for turn in convergent.turns[:2]}
    assert all(turn.stance == previous_stances[turn.speaker]
               for turn in convergent.turns[-2:])
    previous_refs = {ref for turn in non_convergent.turns[:2]
                     for ref in turn.evidence_refs}
    assert any(ref not in previous_refs for turn in non_convergent.turns[-2:]
               for ref in turn.evidence_refs)


def test_invalid_turn_requires_unavailable_quality():
    payload = _load_fixture("normal.json")["transcript"]
    payload["turns"][1]["status"] = "invalid"

    with pytest.raises(ValidationError, match="quality_available"):
        DebateTranscript.model_validate(payload)

    payload["quality_available"] = False
    transcript = DebateTranscript.model_validate(payload)
    assert transcript.turns[1].status == "invalid"
    assert transcript.quality_available is False


def test_unknown_fields_are_rejected(turn_payload):
    turn_payload["unexpected"] = "not part of the contract"

    with pytest.raises(ValidationError, match="unexpected"):
        DebateTurn.model_validate(turn_payload)


def test_schemas_and_package_reexport_the_unique_contract():
    assert schemas.DebateTurn is DebateTurn
    assert schemas.DebateTranscript is DebateTranscript
    assert schemas.Stance is Stance
    assert debate_package.DebateTurn is DebateTurn
    assert debate_package.DebateTranscript is DebateTranscript
    assert debate_package.Stance is Stance


@pytest.mark.parametrize(
    ("prompt", "role", "speaker"),
    [(BULL_PROMPT, "Bull Analyst", "bull"), (BEAR_PROMPT, "Bear Analyst", "bear")],
    ids=["bull", "bear"],
)
def test_prompt_drafts_request_one_json_object_with_the_contract(prompt, role, speaker):
    assert role in prompt
    assert f'speaker 必须为 "{speaker}"' in prompt
    assert "只输出一个 JSON 对象" in prompt
    assert '"market:price"' in prompt
    schema_text = prompt.split("DebateTurn JSON Schema:\n", 1)[1]
    assert json.loads(schema_text) == DebateTurn.model_json_schema()


@pytest.mark.parametrize("text", ["", "  原文\n保持空白  ", '原文包含 {"claim": "示例"}'])
def test_sanitize_stub_returns_the_original_text(text):
    assert sanitize(text) is text
