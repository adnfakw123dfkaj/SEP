"""Stable configuration contract for named analysis profiles."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProfileConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    analysts: tuple[str, ...]
    debate_rounds: int = Field(ge=1)
    risk_rounds: int = Field(ge=1)
    max_tool_rounds: int = Field(ge=1)
    quick_model: str
    deep_model: str
    token_budget: int = Field(gt=0)
    timeout_s: int = Field(gt=0)
    cache_ttl: dict[str, int]
