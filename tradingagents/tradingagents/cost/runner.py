"""Cost-controlled run facade for Part 6 integration tests.

This is a thin composition layer: route -> optional provider call -> monitor
-> quality-floor rollback -> manifest-shaped result.  It deliberately does not
know about LangGraph, reports or the final trading rating; those stay in the
existing pipeline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tradingagents.contracts.cost import Budget, CostReport, PriceTable
from tradingagents.contracts.llm_event import LLMCallEvent, RoutePath
from tradingagents.cost.enforcement import (
    apply_quality_floor,
    handle_budget_exceeded,
)
from tradingagents.cost.monitor import CostMonitor
from tradingagents.cost.router import route


@dataclass(frozen=True)
class CostControlledRunResult:
    """The fields a caller needs to write a manifest and continue the run."""

    route_path: RoutePath
    manifest: dict[str, Any]
    cost_report: CostReport
    provider_calls: int
    final_rating: str | None = None


class CostControlledRunner:
    """Compose routing, monitoring and quality-floor rollback for one run."""

    def __init__(
        self,
        *,
        price_table: PriceTable,
        budget: Budget,
        monitor_factory: Callable[[], CostMonitor] | None = None,
    ):
        self.price_table = price_table
        self.budget = budget
        self._monitor_factory = monitor_factory

    def run(
        self,
        *,
        run_id: str,
        profile: str,
        estimated_tokens: int,
        provider_call: Callable[[], list[LLMCallEvent]],
        quality_floor_pass: bool = True,
    ) -> CostControlledRunResult:
        decision = route(estimated_tokens, self.budget)
        monitor = (
            self._monitor_factory()
            if self._monitor_factory is not None
            else CostMonitor(self.price_table)
        )

        if decision.route_path is RoutePath.HARD_FAIL:
            exceeded = handle_budget_exceeded(
                run_id,
                estimated_tokens,
                self.budget,
                monitor,
            )
            return CostControlledRunResult(
                route_path=RoutePath.HARD_FAIL,
                manifest={
                    "run_id": run_id,
                    "profile": profile,
                    "status": exceeded.status,
                    "route_path": RoutePath.HARD_FAIL.value,
                    "final_rating": exceeded.final_rating,
                    "token_usage_by_agent": exceeded.cost_report.by_agent,
                    "currency": exceeded.cost_report.currency,
                    "price_table_version": exceeded.cost_report.price_table_version,
                    "price_table_source": exceeded.cost_report.price_table_source,
                    "over_budget": exceeded.cost_report.over_budget,
                    "coverage": exceeded.cost_report.coverage,
                    "quality_floor_pass": False,
                    "cost_route_reverted": False,
                    "cache_hits": 0,
                },
                cost_report=exceeded.cost_report,
                provider_calls=0,
                final_rating=exceeded.final_rating,
            )

        events = provider_call()
        for event in events:
            monitor.record(event)

        effective = apply_quality_floor(
            decision,
            quality_floor_pass=quality_floor_pass,
        )
        report = monitor.report(
            run_id,
            self.budget,
            quality_floor_pass=quality_floor_pass,
        )
        reverted = (
            not quality_floor_pass
            and decision.route_path is not RoutePath.DIRECT
        )

        return CostControlledRunResult(
            route_path=effective.route_path,
            manifest={
                "run_id": run_id,
                "profile": profile,
                "status": "completed",
                "route_path": effective.route_path.value,
                "final_rating": None,
                "token_usage_by_agent": report.by_agent,
                "currency": report.currency,
                "price_table_version": report.price_table_version,
                "price_table_source": report.price_table_source,
                "over_budget": report.over_budget,
                "coverage": report.coverage,
                "quality_floor_pass": quality_floor_pass,
                "cost_route_reverted": reverted,
                "cache_hits": sum(1 for event in events if event.cache_hit),
            },
            cost_report=report,
            provider_calls=1,
        )
