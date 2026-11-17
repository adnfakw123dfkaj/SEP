"""Part 6 LLM call event contract.

``LLMCallEvent`` is the single structured record emitted by the provider
adapter for every model call.  Cost aggregation, manifest writing and audit
all consume this object, so its fields and token arithmetic are validated at
the boundary rather than re-checked in every report.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class CallStatus(str, Enum):
    """Terminal or retry state of one provider call."""

    SUCCESS = "success"
    RETRY = "retry"
    FAILURE = "failure"


class RoutePath(str, Enum):
    """Budget route selected before a provider call."""

    DIRECT = "direct"
    SUMMARIZE = "summarize"
    CHEAPER_MODEL = "cheaper_model"
    HARD_FAIL = "hard_fail"


class UsageSource(str, Enum):
    """Where the token counts came from."""

    PROVIDER = "provider"
    ESTIMATED = "estimated"


class LLMCallEvent(BaseModel):
    """One LLM call, with enough context for cost and latency accounting."""

    event_id: str
    run_id: str
    call_id: str
    agent_name: str
    model: str
    provider: str

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)

    latency_ms: float = Field(ge=0)
    status: CallStatus
    retry_count: int = Field(default=0, ge=0)
    route_path: RoutePath
    usage_source: UsageSource
    timestamp: datetime

    cache_hit: bool = False
    tool_name: str | None = None

    @field_validator("timestamp")
    @classmethod
    def _timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        """Peak/off-peak pricing depends on a real instant, not a naive local time."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _token_sum_must_match(self) -> "LLMCallEvent":
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        return self
