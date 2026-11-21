"""Independent provider-usage cost calculation for acceptance audits.

The monitor aggregates cost for the product path.  The audit must not compare
that value with itself, so this module recomputes the same published prices from
raw provider usage events through a separate implementation.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from tradingagents.contracts.cost import PriceTable
from tradingagents.contracts.llm_event import CallStatus, LLMCallEvent, UsageSource

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_MILLION = Decimal(1_000_000)


def _price_phase(timestamp: datetime) -> str:
    local = timestamp.astimezone(_SHANGHAI)
    if local.weekday() >= 5:
        return "off_peak"
    current = local.time()
    if time(9, 0) <= current < time(12, 0):
        return "peak"
    if time(14, 0) <= current < time(18, 0):
        return "peak"
    return "off_peak"


def provider_ground_truth_cost(
    events: Iterable[LLMCallEvent],
    price_table: PriceTable,
    *,
    run_id: str | None = None,
) -> Decimal | None:
    """Recompute cost from provider usage, or return ``None`` when unavailable.

    A failed call contributes no usage and is ignored.  Any successful call with
    estimated usage, or with a model absent from the table, means the audit has
    no independent ground truth for the run.
    """
    priced = [
        event
        for event in events
        if (run_id is None or event.run_id == run_id)
        and event.status is CallStatus.SUCCESS
        and event.total_tokens > 0
    ]
    if not priced:
        return None
    if any(event.usage_source is not UsageSource.PROVIDER for event in priced):
        return None

    total = Decimal(0)
    for event in priced:
        model = price_table.models.get(event.model)
        if model is None:
            return None
        pair = model.peak if _price_phase(event.timestamp) == "peak" else model.off_peak
        total += (
            Decimal(event.prompt_tokens) * pair.input_cache_miss_per_1m
            + Decimal(event.completion_tokens) * pair.output_per_1m
        ) / _MILLION
    return total


__all__ = ["provider_ground_truth_cost"]
