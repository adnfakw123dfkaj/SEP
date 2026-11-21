"""Token/cost audit over many runs for Part 6 acceptance."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from tradingagents.contracts.cost import PriceTable
from tradingagents.contracts.llm_event import RoutePath
from tradingagents.cost.monitor import nearest_rank
from tradingagents.cost.report import compute_report_coverage


class TokenRun(BaseModel):
    """One run's token/cost evidence for the audit."""

    run_id: str
    profile: str
    total_tokens: int = Field(ge=0)
    has_report: bool
    silent_over_budget: bool
    cost: Decimal
    cost_ground_truth: Decimal
    quality_floor_pass: bool
    route_paths: list[RoutePath]
    quality_floor_failures: list[str] = Field(default_factory=list)
    cost_ground_truth_source: Literal["provider", "unavailable"] = "provider"


class TokenReport(BaseModel):
    """Aggregated token/cost evidence for one profile."""

    profile: str
    p95_tokens: int
    report_coverage: float
    silent_over_budget_runs: int
    cost_relative_error: float
    cost_ground_truth_unavailable_runs: int
    quality_floor_pass_rate: float
    routed_quality_floor_pass_rate: float
    currency: Literal["CNY"]
    price_table_version: str
    price_table_source: str


def _relative_error(cost: Decimal, truth: Decimal) -> float:
    if truth == 0:
        return 0.0 if cost == 0 else 1.0
    return float(abs(cost - truth) / abs(truth))


def build_token_report(
    profile: str,
    runs: list[TokenRun],
    price_table: PriceTable,
) -> TokenReport:
    """Aggregate runs for ``profile`` into the acceptance report."""
    selected = [run for run in runs if run.profile == profile]

    token_values = [run.total_tokens for run in selected]
    p95_tokens = int(nearest_rank(token_values, 0.95)) if token_values else 0

    expected_ids = {run.run_id for run in selected}
    reported_ids = {run.run_id for run in selected if run.has_report}
    coverage = compute_report_coverage(expected_ids, reported_ids)

    grounded = [
        run for run in selected if run.cost_ground_truth_source == "provider"
    ]
    errors = [
        _relative_error(run.cost, run.cost_ground_truth)
        for run in grounded
    ]
    # Worst run wins: one 6% error must not hide behind many perfect runs.
    cost_error = max(errors) if errors else 0.0
    unavailable_truth = len(selected) - len(grounded)

    routed = [
        run
        for run in selected
        if any(path is not RoutePath.DIRECT for path in run.route_paths)
    ]
    if routed:
        routed_quality = sum(1 for run in routed if run.quality_floor_pass) / len(routed)
    else:
        routed_quality = 1.0
    quality = (
        sum(1 for run in selected if run.quality_floor_pass) / len(selected)
        if selected
        else 0.0
    )

    return TokenReport(
        profile=profile,
        p95_tokens=p95_tokens,
        report_coverage=coverage,
        silent_over_budget_runs=sum(1 for run in selected if run.silent_over_budget),
        cost_relative_error=cost_error,
        cost_ground_truth_unavailable_runs=unavailable_truth,
        quality_floor_pass_rate=quality,
        routed_quality_floor_pass_rate=routed_quality,
        currency=price_table.currency,
        price_table_version=price_table.version,
        price_table_source=price_table.source_url,
    )


def assert_token_acceptance(report: TokenReport, *, hard_limit: int) -> None:
    """Apply the token/cost acceptance gates."""
    if report.p95_tokens > hard_limit:
        raise AssertionError(
            f"p95 tokens {report.p95_tokens} exceed hard limit {hard_limit}"
        )
    if report.report_coverage != 1.0:
        raise AssertionError(
            f"report coverage {report.report_coverage:.3f} is not 1.0"
        )
    if report.silent_over_budget_runs != 0:
        raise AssertionError(
            f"silent over-budget runs: {report.silent_over_budget_runs}"
        )
    if report.cost_ground_truth_unavailable_runs != 0:
        raise AssertionError(
            "cost ground truth unavailable for "
            f"{report.cost_ground_truth_unavailable_runs} run(s)"
        )
    if report.cost_relative_error > 0.05:
        raise AssertionError(
            f"cost relative error {report.cost_relative_error:.3f} exceeds 0.05"
        )
    if report.quality_floor_pass_rate != 1.0:
        raise AssertionError(
            f"quality floor pass rate {report.quality_floor_pass_rate:.3f} is not 1.0"
        )
    if report.routed_quality_floor_pass_rate != 1.0:
        raise AssertionError(
            "routed runs failed the quality floor: "
            f"{report.routed_quality_floor_pass_rate:.3f}"
        )
    if report.currency != "CNY":
        raise AssertionError(f"expected CNY, got {report.currency!r}")
    if not report.price_table_version or not report.price_table_source:
        raise AssertionError("price table provenance is incomplete")
