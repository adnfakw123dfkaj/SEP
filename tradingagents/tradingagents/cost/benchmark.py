"""Latency report aggregation and acceptance gates for Part 6.

Real 15+15 / 3+3 runs happen in the manual benchmark script; this module only
turns measured samples into a report and applies the agreed gates.  That keeps
the gates testable without network access.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tradingagents.cost.monitor import nearest_rank


class LatencySample(BaseModel):
    """One measured end-to-end latency sample."""

    profile: str
    cache_state: Literal["cold", "warm"]
    duration_s: float = Field(ge=0)
    success: bool = True


class LatencyReport(BaseModel):
    """Aggregated latency evidence for one profile."""

    profile: str
    cold_runs: int
    warm_runs: int
    successful_runs: int
    failed_runs: int
    p50_s: float
    p95_s: float
    p99_s: float
    failure_rate: float
    baseline_p95_s: float | None = None
    improvement: float | None = None


class LatencyPolicy(BaseModel):
    """Profile-specific acceptance policy."""

    require_improvement: bool
    min_improvement: float | None = None
    absolute_p95_target_s: float | None = None


LATENCY_POLICIES: dict[str, LatencyPolicy] = {
    "quick": LatencyPolicy(
        require_improvement=True,
        min_improvement=0.30,
        absolute_p95_target_s=300,
    ),
    "standard": LatencyPolicy(
        require_improvement=True,
        min_improvement=0.30,
        absolute_p95_target_s=720,
    ),
    "deep": LatencyPolicy(
        require_improvement=False,
        absolute_p95_target_s=1800,
    ),
}


def policy_for_profile(profile: str) -> LatencyPolicy:
    """Return the agreed policy, failing loudly for an unknown profile."""
    try:
        return LATENCY_POLICIES[profile]
    except KeyError as exc:
        raise ValueError(f"unknown latency profile {profile!r}") from exc


def summarize_latency(
    profile: str,
    samples: list[LatencySample],
    *,
    baseline_p95_s: float | None = None,
) -> LatencyReport:
    """Summarise samples for ``profile`` using nearest-rank percentiles.

    Failed runs count toward ``failure_rate`` but are excluded from latency
    percentiles, so a timeout cannot masquerade as a very fast run.
    """
    selected = [sample for sample in samples if sample.profile == profile]
    if not selected:
        raise ValueError(f"no latency samples for profile {profile!r}")

    successes = [sample for sample in selected if sample.success]
    durations = [sample.duration_s for sample in successes]

    p50 = nearest_rank(durations, 0.50) if durations else 0.0
    p95 = nearest_rank(durations, 0.95) if durations else 0.0
    p99 = nearest_rank(durations, 0.99) if durations else 0.0
    failure_rate = 1.0 - (len(successes) / len(selected))

    improvement = None
    if baseline_p95_s is not None and baseline_p95_s > 0:
        improvement = (baseline_p95_s - p95) / baseline_p95_s

    return LatencyReport(
        profile=profile,
        cold_runs=sum(1 for sample in selected if sample.cache_state == "cold"),
        warm_runs=sum(1 for sample in selected if sample.cache_state == "warm"),
        successful_runs=len(successes),
        failed_runs=len(selected) - len(successes),
        p50_s=p50,
        p95_s=p95,
        p99_s=p99,
        failure_rate=failure_rate,
        baseline_p95_s=baseline_p95_s,
        improvement=improvement,
    )


def _resolve_policy(
    report: LatencyReport,
    *,
    policy: LatencyPolicy | None,
    require_improvement: bool | None,
    min_improvement: float | None,
    absolute_p95_target_s: float | None,
) -> LatencyPolicy:
    base = policy
    if base is None:
        base = LATENCY_POLICIES.get(report.profile)
    if base is None:
        if (
            require_improvement is None
            and min_improvement is None
            and absolute_p95_target_s is None
        ):
            raise ValueError(
                f"no latency policy for profile {report.profile!r}; "
                "pass a policy or explicit overrides"
            )
        base = LatencyPolicy(require_improvement=True, min_improvement=0.30)

    updates: dict[str, object] = {}
    if require_improvement is not None:
        updates["require_improvement"] = require_improvement
    if min_improvement is not None:
        updates["min_improvement"] = min_improvement
    if absolute_p95_target_s is not None:
        updates["absolute_p95_target_s"] = absolute_p95_target_s
    return base.model_copy(update=updates) if updates else base


def latency_warnings(
    report: LatencyReport,
    *,
    policy: LatencyPolicy | None = None,
) -> list[str]:
    """Non-blocking absolute-p95 warnings for a report's profile."""
    resolved = policy or policy_for_profile(report.profile)
    warnings: list[str] = []
    if (
        resolved.absolute_p95_target_s is not None
        and report.p95_s > resolved.absolute_p95_target_s
    ):
        warnings.append(
            f"absolute p95 {report.p95_s:.1f}s exceeds "
            f"{resolved.absolute_p95_target_s:.1f}s (record-only)"
        )
    return warnings


def assert_latency_acceptance(
    report: LatencyReport,
    *,
    policy: LatencyPolicy | None = None,
    require_improvement: bool | None = None,
    min_improvement: float | None = None,
    absolute_p95_target_s: float | None = None,
) -> list[str]:
    """Apply the agreed latency gates and return non-blocking warnings.

    Failure rate always gates.  Relative improvement gates when the resolved
    policy requires it.  Absolute p95 is record-only and produces a warning,
    never an exception.
    """
    resolved = _resolve_policy(
        report,
        policy=policy,
        require_improvement=require_improvement,
        min_improvement=min_improvement,
        absolute_p95_target_s=absolute_p95_target_s,
    )

    if report.failure_rate > 0.01:
        raise AssertionError(
            f"benchmark failure rate {report.failure_rate:.3f} exceeds 0.01"
        )

    if resolved.require_improvement:
        required = (
            resolved.min_improvement
            if resolved.min_improvement is not None
            else 0.30
        )
        if report.improvement is None:
            raise AssertionError(
                "baseline p95 is required when improvement is required"
            )
        if report.improvement < required:
            raise AssertionError(
                f"p95 improvement {report.improvement:.3f} is below {required:.3f}"
            )

    return latency_warnings(report, policy=resolved)
