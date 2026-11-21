"""Installed vendor implementation versions recorded in the run manifest."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

import tradingagents

_PACKAGES = {
    "yfinance": "yfinance",
    "alpha_vantage": "alpha-vantage",
    "fred": "fredapi",
}
_IMPLEMENTED = {"sec_edgar", "polymarket", "stocktwits", "reddit"}
_ALL = set(_PACKAGES) | _IMPLEMENTED


def _configured(config: dict[str, Any] | None) -> set[str]:
    values: set[str] = set()
    for key in ("data_vendors", "tool_vendors"):
        for raw in ((config or {}).get(key) or {}).values():
            if not isinstance(raw, str):
                continue
            values.update(part.strip() for part in raw.split(",") if part.strip())
    if not values or "default" in values:
        return set(_ALL)
    return {name for name in values if name in _ALL}


def vendor_versions(config: dict[str, Any] | None = None) -> dict[str, str]:
    """Return a version for each configured vendor implementation."""
    result: dict[str, str] = {}
    for name in sorted(_configured(config)):
        package = _PACKAGES.get(name)
        if package is not None:
            try:
                result[name] = version(package)
                continue
            except PackageNotFoundError:
                pass
        result[name] = f"tradingagents-{tradingagents.__version__}"
    return result


__all__ = ["vendor_versions"]
