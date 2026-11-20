"""复用唯一契约，校验发言字段与已有发言之间的关系。"""

from collections.abc import Mapping, Sequence
from typing import Any

from .schemas import DebateTranscript, DebateTurn


def _turn_sequence(transcript: Any) -> Sequence:
    if isinstance(transcript, DebateTranscript):
        return transcript.turns
    if isinstance(transcript, Mapping):
        transcript = transcript.get("turns", ())
    if isinstance(transcript, Sequence) and not isinstance(transcript, (str, bytes)):
        return transcript
    raise ValueError("transcript must contain a sequence of turns")


def _parse_turn(turn: Any) -> DebateTurn:
    # 重新校验模型实例，避免实例在创建后被外部修改而绕过契约。
    if isinstance(turn, DebateTurn):
        turn = turn.model_dump(mode="python")
    return DebateTurn.model_validate(turn)


def validate_turn(
    turn: Any,
    transcript: Any = (),
    *,
    expected_speaker: str | None = None,
    expected_round: int | None = None,
) -> DebateTurn:
    """返回有效发言；引用只能指向传入历史中已经存在的 turn_id。"""
    candidate = _parse_turn(turn)
    previous = [_parse_turn(item) for item in _turn_sequence(transcript)]
    ids = {item.turn_id for item in previous}
    if len(ids) != len(previous) or candidate.turn_id in ids:
        raise ValueError("turn_id must be unique within a transcript")
    if any(right.round <= left.round for left, right in zip(previous, previous[1:])):
        raise ValueError("round must increase monotonically")
    if previous:
        if candidate.round <= previous[-1].round:
            raise ValueError("round must increase monotonically")
        if candidate.speaker == previous[-1].speaker:
            raise ValueError("speakers must alternate")
    if candidate.rebuttal_to is not None and candidate.rebuttal_to not in ids:
        raise ValueError("rebuttal_to must reference an existing earlier turn_id")
    if expected_speaker is not None and candidate.speaker != expected_speaker:
        raise ValueError("speaker does not match the requested speaker")
    if expected_round is not None and candidate.round != expected_round:
        raise ValueError("round does not match the requested round")
    return candidate


def validate_turns(transcript: Any) -> list[DebateTurn]:
    """按已有顺序校验历史，返回新列表，不修改输入。"""
    validated: list[DebateTurn] = []
    for item in _turn_sequence(transcript):
        validated.append(validate_turn(item, validated))
    return validated


__all__ = ["validate_turn"]
