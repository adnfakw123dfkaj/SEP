"""将有序 Transcript 导出为普通字典，不写文件。"""

from collections.abc import Mapping

from .schemas import DebateTranscript, DebateTurn
from .validator import validate_turns


def export_transcript(transcript) -> dict:
    """按 round 排序并重新验证，保留 transcript_id 与质量可用性。"""
    if isinstance(transcript, DebateTranscript):
        payload = transcript.model_dump(mode="python")
    elif isinstance(transcript, Mapping):
        payload = dict(transcript)
    else:
        raise ValueError("transcript must be a DebateTranscript or mapping")
    turns = [
        DebateTurn.model_validate(
            turn.model_dump(mode="python") if isinstance(turn, DebateTurn) else turn
        )
        for turn in payload.get("turns", [])
    ]
    payload["turns"] = validate_turns(sorted(turns, key=lambda turn: turn.round))
    return DebateTranscript.model_validate(payload).model_dump(mode="json")


__all__ = ["export_transcript"]
