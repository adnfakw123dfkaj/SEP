"""Point-in-time coverage of the configured data and memory paths."""

from __future__ import annotations

PIT_COVERAGE: dict[str, str] = {
    "price": "request_date_filter",
    "technical": "request_date_filter",
    "news": "published_window_filter",
    "macro": "observation_date_filter",
    "fundamentals": "filing_date_filter",
    "insider": "withheld_without_disclosure_date",
    "social": "live_only_withheld_historical",
    "identity": "live_profile_withheld_historical",
    "memory": "settled_as_of_filter",
}


def pit_coverage() -> dict[str, str]:
    """Return the coverage policy for every dated or memory-backed path."""
    return dict(PIT_COVERAGE)


__all__ = ["PIT_COVERAGE", "pit_coverage"]
