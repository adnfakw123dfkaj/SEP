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


def resolve_evidence_refs(transcript, registry) -> dict:
    """Attach resolved Part 3 evidence objects to an exported transcript.

    ``DebateTurn.evidence_refs`` remains the stable string wire format. When a
    matching id exists in the run registry, the exported copy also carries the
    full ``EvidenceRef`` so reports can migrate without changing the debate
    contract yet.
    """
    payload = export_transcript(transcript)
    for turn in payload.get("turns", []):
        resolved = []
        for ref_id in turn.get("evidence_refs", []):
            ref = registry.get(ref_id) if registry is not None else None
            if ref is not None:
                resolved.append(ref.model_dump(mode="json"))
        turn["resolved_evidence"] = resolved
    return payload


__all__ = ["export_transcript", "resolve_evidence_refs"]
