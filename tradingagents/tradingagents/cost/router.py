"""Budget routing and context summarisation for Part 6.

Routing is intentionally a pure decision: it does not call providers and does
not mutate run state.  That keeps the hard-fail guarantee testable without
network access.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel

from tradingagents.contracts.cost import Budget, PriceTable
from tradingagents.contracts.llm_event import RoutePath

_SUMMARY_STRING_LIMIT = 500
_SUMMARY_LIST_LIMIT = 20


class RouteDecision(BaseModel):
    """The route chosen for one prospective model call."""

    route_path: RoutePath
    estimated_tokens: int
    reason: str


def route(estimated_tokens: int, budget: Budget) -> RouteDecision:
    """Choose direct, summarise, or hard-fail before a provider call."""
    if estimated_tokens < 0:
        raise ValueError("estimated_tokens must be >= 0")

    if budget.is_hard_exceeded(estimated_tokens):
        return RouteDecision(
            route_path=RoutePath.HARD_FAIL,
            estimated_tokens=estimated_tokens,
            reason="hard budget limit exceeded; provider call blocked",
        )
    if budget.is_soft_exceeded(estimated_tokens):
        return RouteDecision(
            route_path=RoutePath.SUMMARIZE,
            estimated_tokens=estimated_tokens,
            reason="soft budget limit exceeded; summarise before calling",
        )
    return RouteDecision(
        route_path=RoutePath.DIRECT,
        estimated_tokens=estimated_tokens,
        reason="within soft budget; call directly",
    )


def route_after_summary(summary_tokens: int, budget: Budget) -> RouteDecision:
    """Choose the next route after a summary has been produced."""
    if summary_tokens < 0:
        raise ValueError("summary_tokens must be >= 0")

    if budget.is_hard_exceeded(summary_tokens):
        return RouteDecision(
            route_path=RoutePath.HARD_FAIL,
            estimated_tokens=summary_tokens,
            reason="hard budget limit exceeded after summarisation",
        )
    if budget.is_soft_exceeded(summary_tokens):
        return RouteDecision(
            route_path=RoutePath.CHEAPER_MODEL,
            estimated_tokens=summary_tokens,
            reason="still above soft limit after summarisation; use a cheaper model",
        )
    return RouteDecision(
        route_path=RoutePath.DIRECT,
        estimated_tokens=summary_tokens,
        reason="summary brought the call within the soft budget",
    )


def _summarize_value(value: Any, *, protected: bool) -> Any:
    if protected:
        return value
    if isinstance(value, str):
        if len(value) <= _SUMMARY_STRING_LIMIT:
            return value
        return value[:_SUMMARY_STRING_LIMIT] + "…"
    if isinstance(value, Mapping):
        return {
            key: _summarize_value(item, protected=False)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        trimmed = list(value[:_SUMMARY_LIST_LIMIT])
        return [
            _summarize_value(item, protected=False)
            for item in trimmed
        ]
    return value


def summarize_context(
    context: Mapping[str, Any],
    *,
    protected_keys: Iterable[str] = (),
) -> dict[str, Any]:
    """Return a shortened copy while preserving decision-critical keys."""
    protected = frozenset(protected_keys)
    return {
        key: _summarize_value(value, protected=key in protected)
        for key, value in context.items()
    }


def select_cheaper_model(
    model: str,
    *,
    price_table: PriceTable,
    allowed_models: Iterable[str] | None = None,
) -> str:
    """Pick the least expensive allowed model by off-peak input+output price."""
    if model not in price_table.models:
        raise ValueError(f"model {model!r} is not present in the price table")

    if allowed_models is None:
        candidates = set(price_table.models)
    else:
        candidates = set(allowed_models) & set(price_table.models)

    if not candidates:
        raise ValueError("no allowed models are present in the price table")

    def score(candidate: str) -> tuple[Any, str]:
        price = price_table.models[candidate].off_peak
        return (price.input_cache_miss_per_1m + price.output_per_1m, candidate)

    return min(candidates, key=score)
