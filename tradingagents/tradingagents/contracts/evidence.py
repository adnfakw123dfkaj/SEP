"""Part 3 evidence reference contract.

``EvidenceRef`` points a substantive claim in a report at the exact data it rests
on: a tool call's result, a market snapshot, a news or social item. The report
writer emits a ref per claim, and the faithfulness checker resolves each ref back
to the recorded source so a number can be traced, not trusted.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_VALID_KINDS = ("tool", "snapshot", "news", "social", "statement", "memory")


class EvidenceRef(BaseModel):
    """One traceable source backing a claim."""

    kind: str = Field(description="tool | snapshot | news | social | statement | memory")
    id: str = Field(min_length=1, description="Stable id of the source, e.g. a call_id")
    source: str = Field(default="", description="Human label: tool name, publisher, subreddit")
    snapshot_hash: str | None = Field(default=None, description="Hash of the exact payload used")
    retrieved_at: datetime | None = Field(default=None, description="When the source was fetched")

    @field_validator("kind")
    @classmethod
    def _kind_known(cls, value: str) -> str:
        if value not in _VALID_KINDS:
            raise ValueError(f"unknown evidence kind: {value!r}")
        return value
