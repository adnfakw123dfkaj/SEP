"""Report-level helpers shared by the monitor and token audit."""

from __future__ import annotations

from collections.abc import Iterable


def compute_report_coverage(
    run_ids: Iterable[str],
    report_run_ids: Iterable[str],
) -> float:
    """Fraction of expected runs that produced a token/cost report."""
    expected = set(run_ids)
    if not expected:
        return 0.0
    reported = set(report_run_ids)
    return len(expected & reported) / len(expected)
