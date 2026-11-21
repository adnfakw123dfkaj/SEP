"""Part 2 的唯一辩论字段定义；只包含数据契约及其一致性约束。"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Stance(StrEnum):
    """发言表达的立场，与发言者角色分开记录。"""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class DebateTurn(BaseModel):
    """一次结构化发言；引用的存在性由所属 Transcript 校验。"""

    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(min_length=1)
    round: int = Field(ge=1, strict=True)
    speaker: Literal["bull", "bear"]
    claim: str = Field(min_length=1)
    stance: Stance
    evidence_refs: list[str]
    assumptions: list[str]
    rebuttal_to: str | None
    confidence: float = Field(ge=0, le=1, strict=True, allow_inf_nan=False)
    open_questions: list[str]
    requested_evidence: list[str]
    no_new_evidence: bool = Field(default=False, strict=True)
    status: Literal["ok", "invalid"] = "ok"

    @field_validator("turn_id", "claim", "rebuttal_to")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("text must not be blank")
        return value

    @field_validator("evidence_refs")
    @classmethod
    def _nonblank_refs(cls, refs: list[str]) -> list[str]:
        if any(not ref.strip() for ref in refs):
            raise ValueError("evidence_refs must contain nonblank strings")
        return refs

    @model_validator(mode="after")
    def _requires_evidence_or_explicit_absence(self) -> "DebateTurn":
        if not self.evidence_refs and not self.no_new_evidence:
            raise ValueError("evidence_refs required unless no_new_evidence is true")
        return self


class DebateTranscript(BaseModel):
    """同一辩论中的有序发言及质量指标可用性声明。"""

    model_config = ConfigDict(extra="forbid")

    transcript_id: str = Field(min_length=1)
    turns: list[DebateTurn]
    quality_available: bool = Field(strict=True)

    @field_validator("transcript_id")
    @classmethod
    def _nonblank_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transcript_id must not be blank")
        return value

    @model_validator(mode="after")
    def _consistent_turns(self) -> "DebateTranscript":
        seen: set[str] = set()
        for turn in self.turns:
            if turn.turn_id in seen:
                raise ValueError("turn_id must be unique within a transcript")
            if turn.rebuttal_to is not None and turn.rebuttal_to not in seen:
                raise ValueError("rebuttal_to must reference an existing earlier turn_id")
            seen.add(turn.turn_id)
        if self.quality_available and any(turn.status == "invalid" for turn in self.turns):
            raise ValueError("invalid turns require quality_available to be false")
        return self


__all__ = ["DebateTranscript", "DebateTurn", "Stance"]
