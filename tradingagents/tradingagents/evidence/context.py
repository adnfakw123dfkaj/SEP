"""Run-scoped evidence registry and tool-result capture."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from tradingagents.contracts import EvidenceRef

from .registry import EvidenceRegistry

_registry: ContextVar[EvidenceRegistry | None] = ContextVar(
    "evidence_registry", default=None
)


def current_evidence_registry() -> EvidenceRegistry | None:
    """The registry bound to the current run, if any."""
    return _registry.get()


@contextmanager
def evidence_scope(registry: EvidenceRegistry | None = None):
    """Bind a registry for one run and restore the previous one afterwards."""
    active = registry or EvidenceRegistry()
    token = _registry.set(active)
    try:
        yield active
    finally:
        _registry.reset(token)


def _hash_payload(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def register_tool_result(
    *,
    method: str,
    vendor: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    value: Any,
    cache_hit: bool = False,
) -> EvidenceRef | None:
    """Register one tool result as an ``EvidenceRef`` in the active run."""
    registry = _registry.get()
    if registry is None:
        return None

    call_id = "tool-" + _hash_payload(
        {
            "method": method,
            "vendor": vendor,
            "args": args,
            "kwargs": kwargs,
            "cache_hit": cache_hit,
        }
    )[:16]
    snapshot_hash = _hash_payload(value)[:16]
    ref = EvidenceRef(
        kind="tool",
        id=call_id,
        source=f"{method}:{vendor}" + (":cache" if cache_hit else ""),
        snapshot_hash=snapshot_hash,
        retrieved_at=datetime.now(UTC),
    )
    registry.register(ref)
    if method == "get_verified_market_snapshot" and isinstance(value, str):
        registry.register_snapshot(value)
    return ref


__all__ = [
    "current_evidence_registry",
    "evidence_scope",
    "register_tool_result",
]
