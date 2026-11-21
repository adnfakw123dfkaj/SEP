"""Synchronous, pre-LLM ticker and price-data preflight."""
from __future__ import annotations

import re
from tradingagents.contracts.preflight import PreflightResult

_TICKER = re.compile(r"^[A-Z0-9^][A-Z0-9.^=_+-]{0,31}$")


def validate_request(ticker: str, date: str | None = None, profile=None) -> PreflightResult:
    """Check symbol shape and whether Yahoo returns usable history.

    Provider/network errors are reported as unavailable data (not invalid symbol).
    This performs no LLM calls.
    """
    raw = ticker.strip().upper() if isinstance(ticker, str) else ""
    if not raw or not _TICKER.fullmatch(raw):
        return PreflightResult(ticker=raw, resolved=False, data_available=False,
                               reason="ticker is empty or has an invalid format")
    try:
        from tradingagents.dataflows.symbols import normalize_symbol
        from tradingagents.dataflows.date_window import get_current_date
        from tradingagents.dataflows.router import route_to_vendor
        as_of = date or get_current_date()
        data = route_to_vendor("get_stock_data", normalize_symbol(raw), "2020-01-01", as_of)
        if not data or "no data available" in str(data).lower():
            return PreflightResult(ticker=raw, resolved=True, tradable=None, data_available=False,
                                   reason="no price history returned by data provider")
        if "vendor unavailable" in str(data).lower() or "error:" in str(data).lower():
            return PreflightResult(ticker=raw, resolved=True, tradable=None, data_available=False,
                                   reason="data provider unavailable")
        return PreflightResult(ticker=raw, resolved=True, tradable=True, data_available=True)
    except Exception as exc:
        return PreflightResult(ticker=raw, resolved=True, tradable=None, data_available=False,
                               reason=f"data provider unavailable: {type(exc).__name__}")
