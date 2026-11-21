"""Claim-level evidence records for report faithfulness audits."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReportClaim(BaseModel):
    """One report claim group and the evidence that supports it."""

    claim_id: str = Field(min_length=1)
    section: str = Field(min_length=1)
    kind: Literal["numeric", "qualitative"]
    text: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    snapshot_hashes: list[str] = Field(default_factory=list)


__all__ = ["ReportClaim"]
