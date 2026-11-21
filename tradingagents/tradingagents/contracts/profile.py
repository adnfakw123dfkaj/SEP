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
    max_tool_output_chars: int = Field(default=6000, gt=0)
    report_prompt_chars: int = Field(default=4000, gt=0)
    max_output_tokens: int = Field(default=4096, gt=0)
