"""Part 6 performance and cost control."""

from .agent_context import agent_scope, current_agent, with_agent_scope
from .audit import TokenReport, TokenRun, assert_token_acceptance, build_token_report
from .benchmark import (
    LATENCY_POLICIES,
    LatencyPolicy,
    LatencyReport,
    LatencySample,
    assert_latency_acceptance,
    latency_warnings,
    policy_for_profile,
    summarize_latency,
)
from .budget import budget_for_profile
from .callback import CostTrackingCallback
from .enforcement import (
    BudgetExceededError,
    BudgetExceededResult,
    apply_quality_floor,
    guarded_call,
    handle_budget_exceeded,
)
from .estimator import estimate_tokens
from .guard import GuardedLLM, GuardedRunnable
from .monitor import CostMonitor, nearest_rank, price_phase
from .pricing import default_price_table
from .report import compute_report_coverage
from .router import (
    RouteDecision,
    route,
    route_after_summary,
    select_cheaper_model,
    summarize_context,
)
from .runner import CostControlledRunner, CostControlledRunResult

__all__ = [
    "BudgetExceededError",
    "BudgetExceededResult",
    "CostControlledRunResult",
    "agent_scope",
    "current_agent",
    "with_agent_scope",
    "CostControlledRunner",
    "CostMonitor",
    "CostTrackingCallback",
    "GuardedLLM",
    "GuardedRunnable",
    "LATENCY_POLICIES",
    "LatencyPolicy",
    "LatencyReport",
    "LatencySample",
    "RouteDecision",
    "TokenReport",
    "TokenRun",
    "apply_quality_floor",
    "assert_latency_acceptance",
    "assert_token_acceptance",
    "budget_for_profile",
    "build_token_report",
    "compute_report_coverage",
    "default_price_table",
    "estimate_tokens",
    "guarded_call",
    "handle_budget_exceeded",
    "latency_warnings",
    "nearest_rank",
    "policy_for_profile",
    "price_phase",
    "route",
    "route_after_summary",
    "select_cheaper_model",
    "summarize_context",
    "summarize_latency",
]
