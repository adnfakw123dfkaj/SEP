"""Contracts for provenance-aware local data caching."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class CacheKey(BaseModel):
    data_class: str = Field(min_length=1)
    source: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    as_of: str | None = None
    version: str = "1"


class TTLPolicy(BaseModel):
    seconds: int = Field(gt=0)

    @classmethod
    def for_data_class(cls, data_class: str) -> "TTLPolicy":
        return cls(seconds={"price": 900, "technical": 900, "news": 3600,
                            "social": 3600, "fundamental": 86400,
                            "identity": 604800, "preflight_price": 900,
                            "preflight_identity": 604800}.get(data_class, 3600))

    @classmethod
    def for_request(cls, data_class: str, *, market_open: bool = True) -> "TTLPolicy":
        if data_class == "price" and not market_open:
            return cls(seconds=86400)
        return cls.for_data_class(data_class)


class CacheEntry(BaseModel):
    value: Any
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime

    def is_fresh(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now < self.expires_at
