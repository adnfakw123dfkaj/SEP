"""Part 3 run manifest contract.

``RunManifest`` is the single structured record written per run: what was
analysed, with which models/profile/vendors, what it cost in tokens, what
fallback/security events happened, the final rating, and the run status. It is the
evidence artifact behind auditing, replay, cost attribution and latency/cost
acceptance. The manifest stores metadata only — never raw vendor payloads.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

_VALID_STATUS = ("completed", "failed", "review", "partial")


class RunManifest(BaseModel):
    """Structured, per-run metadata record."""

    run_id: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    date: str = Field(min_length=1)
    profile: str = "standard"
    analysts: list[str] = Field(default_factory=list)
    models: dict[str, str] = Field(default_factory=dict)
    provider: str = ""
    prompt_version: str = ""
    config_hash: str = ""
    vendor_versions: dict[str, str] = Field(default_factory=dict)
    cache_hits: int = Field(default=0, ge=0)
    token_usage_by_agent: dict[str, int] = Field(default_factory=dict)
    cost_estimate: float | None = None
    fallback_events: list[str] = Field(default_factory=list)
    security_events: list[str] = Field(default_factory=list)
    rating: str | None = None
    timestamps: dict[str, str] = Field(default_factory=dict)
    status: str = "completed"

    @field_validator("status")
    @classmethod
    def _status_known(cls, value: str) -> str:
        if value not in _VALID_STATUS:
            raise ValueError(f"unknown status: {value!r}")
        return value

    @field_validator("token_usage_by_agent")
    @classmethod
    def _non_negative_tokens(cls, value: dict[str, int]) -> dict[str, int]:
        for agent, tokens in value.items():
            if tokens < 0:
                raise ValueError(f"token usage for {agent!r} is negative")
        return value

    def total_tokens(self) -> int:
        """Sum of per-agent token usage."""
        return sum(self.token_usage_by_agent.values())

    def add_fallback_events(self, events) -> None:
        """Append typed fallback events as compact JSON metadata for audit."""
        from json import dumps

        for event in events:
            payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else event
            self.fallback_events.append(dumps(payload, sort_keys=True, ensure_ascii=False))

    @model_validator(mode="after")
    def _timestamps_parse(self) -> RunManifest:
        for key, value in self.timestamps.items():
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"timestamp {key!r} is not ISO-8601: {value!r}") from exc
        return self
