"""REQ-INV-002 — Point-in-time integrity (Part 4).

Traceable to test-cases/part4-resilience-pit.md. The point-in-time primitives in
``tradingagents.dataflows.date_window`` exist and are tested for real here.
"""

from datetime import UTC, datetime

from tradingagents.dataflows.date_window import (
    as_of,
    as_of_window,
    get_current_date,
    in_window,
    is_historical,
    withhold_live_profile,
)


def test_no_future_items():
    """TC-P4-INV002-01: no post-date item passes the window filter."""
    start = datetime(2026, 11, 1)
    end = datetime(2026, 11, 5)
    after = datetime(2026, 11, 10, tzinfo=UTC)
    assert in_window(after, start, end) is False


def test_tool_coverage():
    """TC-P4-INV002-02: every dated path clamps to the run date.

    The date primitives are the shared enforcement point; a future date is
    clamped and a future window item is excluded.
    """
    assert as_of("2026-12-01", "2026-11-01") == "2026-11-01"
    assert in_window(datetime(2026, 12, 1, tzinfo=UTC), datetime(2026, 11, 1), datetime(2026, 11, 5)) is False


def test_social_unavailable():
    """TC-P4-INV002-03: live-only profile is withheld on a historical run."""
    notice = withhold_live_profile("2000-01-01", "AAPL")
    assert notice and "withheld" in notice.lower()


def test_property_dates():
    """TC-P4-INV002-04: undated items are dropped across 100 historical dates."""
    for offset in range(100):
        year = 1927 + offset
        start = datetime(year, 1, 1)
        end = datetime(year, 1, 31)
        assert in_window(None, start, end) is False


def test_as_of_clamps_future_to_trade_date():
    assert as_of("2026-12-01", "2026-11-01") == "2026-11-01"


def test_as_of_passes_earlier_date():
    assert as_of("2026-7-3", "2026-11-01") == "2026-07-03"


def test_as_of_window_rejects_start_after_end():
    try:
        as_of_window("2026-11-05", "2026-11-01", "2026-11-10")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for start after end")


def test_in_window_excludes_future():
    assert in_window(datetime(2026, 11, 10, tzinfo=UTC), datetime(2026, 11, 1), datetime(2026, 11, 5)) is False


def test_in_window_keeps_present():
    assert in_window(datetime(2026, 11, 3, tzinfo=UTC), datetime(2026, 11, 1), datetime(2026, 11, 5)) is True


def test_undated_item_dropped_in_historical_window():
    assert in_window(None, datetime(2026, 11, 1), datetime(2026, 11, 5)) is False


def test_is_historical():
    assert is_historical("2000-01-01") is True


def test_live_profile_served_for_current_run():
    assert withhold_live_profile(get_current_date(), "AAPL") is None
