"""Synchronous, pre-LLM ticker and price-data preflight."""
import re

from tradingagents.contracts.cache import CacheKey
from tradingagents.contracts.preflight import PreflightResult

_TICKER = re.compile(r"^[A-Z0-9^][A-Z0-9.^=_+-]{0,31}$")


def _cache_for(config: dict | None):
    """A disk cache when the caller supplied a run config; tests stay side-effect free."""
    if not config:
        return None
    root = config.get("data_cache_dir")
    if not root:
        return None
    from tradingagents.cache import CacheController

    return CacheController(root)


def _identity(raw: str, cache) -> dict:
    """Resolve and cache instrument identity for the 7-day identity TTL."""
    if cache is None:
        return {}
    from tradingagents.agents.context import resolve_instrument_identity

    key = CacheKey(data_class="preflight_identity", source="preflight", subject=raw)
    entry = cache.get(key)
    if entry is not None:
        return entry.value if isinstance(entry.value, dict) else {}

    identity = resolve_instrument_identity(raw)
    if identity:
        cache.set(key, identity, {"resolver": "instrument_identity"})
    return identity


def _price_data(raw: str, as_of: str, cache):
    """Fetch usable price history, caching only successful responses."""
    from tradingagents.dataflows.router import route_to_vendor
    from tradingagents.dataflows.symbols import normalize_symbol

    symbol = normalize_symbol(raw)
    key = CacheKey(
        data_class="preflight_price",
        source="preflight",
        subject=symbol,
        parameters={"start": "2020-01-01", "end": as_of},
        as_of=as_of,
    )
    if cache is not None:
        entry = cache.get(key)
        if entry is not None:
            return entry.value

    data = route_to_vendor("get_stock_data", symbol, "2020-01-01", as_of)
    text = str(data).lower() if data is not None else ""
    unusable = (
        "no data available" in text
        or "no_data_available" in text
        or "data_unavailable" in text
        or "vendor unavailable" in text
        or "error:" in text
    )
    usable = bool(data) and not unusable
    if cache is not None and usable:
        cache.set(key, data, {"vendor": "router"})
    return data


def validate_request(
    ticker: str,
    date: str | None = None,
    profile=None,
    config: dict | None = None,
) -> PreflightResult:
    """Check symbol shape, identity and price-data availability before the graph.

    Provider/network errors are reported as unavailable data (not invalid symbol).
    This performs no LLM calls. When ``config`` is supplied, identity and price
    lookups use the configured disk cache with the preflight TTLs.
    """
    raw = ticker.strip().upper() if isinstance(ticker, str) else ""
    if not raw or not _TICKER.fullmatch(raw):
        return PreflightResult(ticker=raw, resolved=False, data_available=False,
                               reason="ticker is empty or has an invalid format")
    cache = _cache_for(config)
    _identity(raw, cache)
    try:
        from tradingagents.dataflows.date_window import get_current_date

        as_of = date or get_current_date()
        data = _price_data(raw, as_of, cache)
        text = str(data).lower() if data is not None else ""
        if not data or "no data available" in text or "no_data_available" in text:
            return PreflightResult(ticker=raw, resolved=True, tradable=None, data_available=False,
                                   reason="no price history returned by data provider")
        if (
            "vendor unavailable" in text
            or "data_unavailable" in text
            or "error:" in text
        ):
            return PreflightResult(ticker=raw, resolved=True, tradable=None, data_available=False,
                                   reason="data provider unavailable")
        return PreflightResult(ticker=raw, resolved=True, tradable=True, data_available=True)
    except Exception as exc:
        return PreflightResult(ticker=raw, resolved=True, tradable=None, data_available=False,
                               reason=f"data provider unavailable: {type(exc).__name__}")
