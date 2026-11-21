"""Part 6 cost, budget and price-table contracts.

These models are the machine-readable boundary between the estimator,
router, monitor and report layers.  Prices are CNY per million tokens,
matching the official DeepSeek pricing page; cache pricing is intentionally
modelled as cache-miss only for this release.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .llm_event import RoutePath


class TokenEstimate(BaseModel):
    """Estimated input/output cost driver for one prospective model call."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    confidence: Literal["low", "medium", "high"]

    @model_validator(mode="after")
    def _total_must_match(self) -> "TokenEstimate":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens + output_tokens")
        return self


class Budget(BaseModel):
    """Per-profile token budget with inclusive soft/hard boundaries."""

    profile: str
    soft_limit: int = Field(gt=0)
    hard_limit: int = Field(gt=0)
    currency: Literal["CNY"] = "CNY"

    @model_validator(mode="after")
    def _soft_must_not_exceed_hard(self) -> "Budget":
        if self.soft_limit > self.hard_limit:
            raise ValueError("soft_limit must be <= hard_limit")
        return self

    def is_soft_exceeded(self, estimated_tokens: int) -> bool:
        return estimated_tokens >= self.soft_limit

    def is_hard_exceeded(self, estimated_tokens: int) -> bool:
        return estimated_tokens >= self.hard_limit


class PricePair(BaseModel):
    """Cache-miss input and output prices for one phase, per 1M tokens."""

    input_cache_miss_per_1m: Decimal = Field(ge=0)
    output_per_1m: Decimal = Field(ge=0)


class ModelPrice(BaseModel):
    """Published prices for one model in both peak and off-peak phases."""

    model: str
    model_version: str
    peak: PricePair
    off_peak: PricePair
    cache_hit_input_per_1m: Decimal | None = None


class PriceTable(BaseModel):
    """Versioned, source-linked price table."""

    currency: Literal["CNY"]
    version: str
    source_url: str
    retrieved_at: date
    models: dict[str, ModelPrice]


class CostReport(BaseModel):
    """Aggregated token/cost evidence for one run."""

    run_id: str
    profile: str

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)

    by_agent: dict[str, int]
    by_model: dict[str, int]
    by_tool: dict[str, int]

    cost: Decimal
    currency: Literal["CNY"] = "CNY"
    price_table_version: str
    price_table_source: str
    peak_policy: str
    cache_policy: str

    coverage: float = Field(ge=0.0, le=1.0)
    over_budget: bool
    route_paths: list[RoutePath]
    quality_floor_pass: bool
