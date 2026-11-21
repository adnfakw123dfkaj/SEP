"""Input gate result returned before an analysis graph is started."""
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class PreflightResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    ticker: str
    resolved: bool
    tradable: bool | None = None
    data_available: bool
    reason: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def ok(self) -> bool:
        return self.resolved and self.data_available
