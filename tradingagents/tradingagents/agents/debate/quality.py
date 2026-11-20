"""REQ-QUAL-001 的确定性质量代理指标；不调用模型，也不修改输入。"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from unicodedata import category

from .schemas import DebateTranscript, DebateTurn

# 规范化后的相似度 >= 0.95 视为重复；固定阈值，禁用自动启发式过滤。
CLAIM_SIMILARITY_THRESHOLD = 0.95
# 验收阈值：证据覆盖 == 1.0，反驳覆盖 >= 0.90，
# 无证据断言率 <= 0.05，重复主张率 <= 0.10。


@dataclass(frozen=True, slots=True)
class QualityMetrics:
    """quality_available 仅表示可计算；是否达标需逐项比较验收阈值。"""

    turns_with_evidence_or_no_new_evidence_rate: float | None = None
    rebuttal_coverage: float | None = None
    unsupported_claim_rate: float | None = None
    duplicate_claim_rate: float | None = None
    quality_available: bool = False


def _normalize_claim(claim: str) -> str:
    """统一大小写，将连续空白及 Unicode 标点合并为空格。"""
    separated = "".join(
        " " if char.isspace() or category(char).startswith("P") else char
        for char in claim.casefold().strip()
    )
    return " ".join(separated.split())


def _is_duplicate(claim: str, previous_claims: list[str]) -> bool:
    return any(
        claim == previous
        or SequenceMatcher(None, previous, claim, autojunk=False).ratio()
        >= CLAIM_SIMILARITY_THRESHOLD
        for previous in previous_claims
    )


def score_debate(
    transcript: DebateTranscript | Mapping[str, object],
) -> QualityMetrics:
    """按原始发言顺序计分；不可用时四项数值均为 None。

    不调用契约校验器：缺少证据和错误反驳引用本身就是需要计分的缺陷。
    仅有开场发言时没有反驳义务，反驳覆盖率按 1.0 计算。
    """
    if isinstance(transcript, DebateTranscript):
        turns = transcript.turns
        available = transcript.quality_available
    elif isinstance(transcript, Mapping):
        turns = transcript.get("turns")
        available = transcript.get("quality_available", False)
    else:
        return QualityMetrics()

    if (
        available is not True
        or not isinstance(turns, Sequence)
        or isinstance(turns, (str, bytes))
        or not turns
    ):
        return QualityMetrics()

    evidence_covered = rebuttals = unsupported = duplicates = 0
    previous_ids: set[str] = set()
    previous_claims: list[str] = []
    for index, turn in enumerate(turns):
        if isinstance(turn, DebateTurn):
            turn = turn.model_dump(mode="python")
        if not isinstance(turn, Mapping) or turn.get("status", "ok") != "ok":
            return QualityMetrics()

        turn_id = turn.get("turn_id")
        claim = turn.get("claim")
        refs = turn.get("evidence_refs")
        no_new_evidence = turn.get("no_new_evidence", False)
        if (
            not isinstance(turn_id, str)
            or not turn_id.strip()
            or not isinstance(claim, str)
            or not claim.strip()
            or not isinstance(refs, list)
            or not all(isinstance(ref, str) and ref.strip() for ref in refs)
            or not isinstance(no_new_evidence, bool)
        ):
            return QualityMetrics()

        evidence_covered += bool(refs) or no_new_evidence
        # 无新增证据仍计入无证据断言；不能用 no_new_evidence 豁免此指标。
        unsupported += not refs
        target = turn.get("rebuttal_to")
        if index > 0 and isinstance(target, str) and target in previous_ids:
            rebuttals += 1
        previous_ids.add(turn_id)

        normalized = _normalize_claim(claim)
        duplicates += _is_duplicate(normalized, previous_claims)
        previous_claims.append(normalized)

    total = len(turns)
    return QualityMetrics(
        turns_with_evidence_or_no_new_evidence_rate=evidence_covered / total,
        rebuttal_coverage=rebuttals / (total - 1) if total > 1 else 1.0,
        unsupported_claim_rate=unsupported / total,
        duplicate_claim_rate=duplicates / total,
        quality_available=True,
    )


__all__ = ["QualityMetrics", "score_debate"]
