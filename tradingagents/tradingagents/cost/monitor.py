"""Cost aggregation for Part 6.

The monitor turns ``LLMCallEvent`` records into a ``CostReport``.  It is the
only place that applies the CNY price table, peak/off-peak phase and
cache-miss policy; callers never recompute cost themselves.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time
from decimal import Decimal
from math import ceil
from zoneinfo import ZoneInfo

from tradingagents.contracts.cost import Budget, CostReport, PriceTable
from tradingagents.contracts.llm_event import LLMCallEvent, RoutePath

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_MILLION = Decimal(1_000_000)
_PEAK_POLICY = "weekday_hours_ignore_holidays"
_CACHE_POLICY = "cache_miss"


def price_phase(timestamp: datetime) -> str:
    """Return ``peak`` or ``off_peak`` using Beijing weekday hours.

    Holidays are intentionally ignored, per the agreed policy: a weekday
    holiday inside 09:00-12:00 or 14:00-18:00 is still priced as peak.
    """
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")

    local = timestamp.astimezone(_SHANGHAI)
    if local.weekday() >= 5:
        return "off_peak"

    current = local.time()
    morning = time(9, 0) <= current < time(12, 0)
    afternoon = time(14, 0) <= current < time(18, 0)
    return "peak" if morning or afternoon else "off_peak"


def nearest_rank(values: Sequence[float], percentile: float) -> float:
    """Nearest-rank percentile (p50=50, p95=95 for 1..100)."""
    if not values:
        raise ValueError("nearest_rank requires at least one value")
    if not 0.0 <= percentile <= 1.0:
        raise ValueError("percentile must be in [0, 1]")

    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, ceil(percentile * len(ordered)) - 1))
    return ordered[index]


class CostMonitor:
    """Collects call events for one run and emits a cost report."""

    def __init__(self, price_table: PriceTable):
        self.price_table = price_table
        self._events: list[LLMCallEvent] = []

    def record(self, event: LLMCallEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> tuple[LLMCallEvent, ...]:
        return tuple(self._events)

    def report(
        self,
        run_id: str,
        budget: Budget,
        *,
        quality_floor_pass: bool,
        over_budget: bool | None = None,
    ) -> CostReport:
        events = tuple(event for event in self._events if event.run_id == run_id)
        prompt_tokens = sum(event.prompt_tokens for event in events)
        completion_tokens = sum(event.completion_tokens for event in events)
        total_tokens = sum(event.total_tokens for event in events)

        by_agent: dict[str, int] = {}
        by_model: dict[str, int] = {}
        by_tool: dict[str, int] = {}
        route_paths: list[RoutePath] = []
        cost = Decimal(0)

        for event in events:
            by_agent[event.agent_name] = by_agent.get(event.agent_name, 0) + event.total_tokens
            by_model[event.model] = by_model.get(event.model, 0) + event.total_tokens
            tool = event.tool_name or "unknown"
            by_tool[tool] = by_tool.get(tool, 0) + event.total_tokens
            if event.route_path not in route_paths:
                route_paths.append(event.route_path)

            model_price = self.price_table.models.get(event.model)
            if model_price is None:
                raise ValueError(
                    f"model {event.model!r} is missing from price table "
                    f"{self.price_table.version!r}"
                )
            phase = price_phase(event.timestamp)
            pair = model_price.peak if phase == "peak" else model_price.off_peak
            cost += (
                Decimal(event.prompt_tokens) * pair.input_cache_miss_per_1m
                + Decimal(event.completion_tokens) * pair.output_per_1m
            ) / _MILLION

        return CostReport(
            run_id=run_id,
            profile=budget.profile,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            by_agent=by_agent,
            by_model=by_model,
            by_tool=by_tool,
            cost=cost,
            currency=self.price_table.currency,
            price_table_version=self.price_table.version,
            price_table_source=self.price_table.source_url,
            peak_policy=_PEAK_POLICY,
            cache_policy=_CACHE_POLICY,
            coverage=1.0,
            over_budget=(
                budget.is_hard_exceeded(total_tokens) if over_budget is None else over_budget
            ),
            route_paths=route_paths,
            quality_floor_pass=quality_floor_pass,
        )
