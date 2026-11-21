"""Hard-fail guarantees and quality-floor rollback for Part 6."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypeVar

from pydantic import BaseModel

from tradingagents.contracts.cost import Budget, CostReport
from tradingagents.contracts.llm_event import RoutePath
from tradingagents.cost.monitor import CostMonitor
from tradingagents.cost.router import RouteDecision, route

T = TypeVar("T")

_EXIT_BUDGET_EXCEEDED = 2


class BudgetExceededError(RuntimeError):
    """Raised before a provider call when the hard budget would be exceeded."""


class BudgetExceededResult(BaseModel):
    """The auditable record produced by a hard budget stop."""

    status: Literal["budget_exceeded"]
    final_rating: Literal["REVIEW"]
    exit_code: int
    estimated_tokens: int
    budget: Budget
    cost_report: CostReport


def guarded_call(
    estimated_tokens: int,
    budget: Budget,
    call: Callable[[], T],
) -> T:
    """Run ``call`` only when the route is not ``hard_fail``."""
    decision = route(estimated_tokens, budget)
    if decision.route_path is RoutePath.HARD_FAIL:
        raise BudgetExceededError(
            f"budget hard limit exceeded: estimated={estimated_tokens}, "
            f"hard={budget.hard_limit}"
        )
    return call()


def handle_budget_exceeded(
    run_id: str,
    estimated_tokens: int,
    budget: Budget,
    monitor: CostMonitor,
) -> BudgetExceededResult:
    """Build the hard-fail record without calling the provider."""
    if not budget.is_hard_exceeded(estimated_tokens):
        raise ValueError("handle_budget_exceeded called without a hard-limit breach")

    report = monitor.report(
        run_id,
        budget,
        quality_floor_pass=False,
        over_budget=True,
    )
    return BudgetExceededResult(
        status="budget_exceeded",
        final_rating="REVIEW",
        exit_code=_EXIT_BUDGET_EXCEEDED,
        estimated_tokens=estimated_tokens,
        budget=budget,
        cost_report=report,
    )


def apply_quality_floor(
    decision: RouteDecision,
    *,
    quality_floor_pass: bool,
) -> RouteDecision:
    """Revert a cost-saving route when the routed run failed its quality floor."""
    if quality_floor_pass or decision.route_path is RoutePath.DIRECT:
        return decision

    return RouteDecision(
        route_path=RoutePath.DIRECT,
        estimated_tokens=decision.estimated_tokens,
        reason="quality floor failed; cost route reverted to direct",
    )
