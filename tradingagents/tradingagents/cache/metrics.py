"""Run-scoped cache metrics for Part 4 evidence."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    writes: int = 0
    write_skipped: int = 0
    stale_reads: int = 0

    def as_dict(self) -> dict[str, int | float]:
        requests = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
            "write_skipped": self.write_skipped,
            "stale_reads": self.stale_reads,
            "hit_rate": (self.hits / requests) if requests else 0.0,
        }


_metrics: ContextVar[CacheMetrics | None] = ContextVar("cache_metrics", default=None)
_lock = threading.Lock()


@contextmanager
def cache_metrics_scope(metrics: CacheMetrics | None = None) -> Iterator[CacheMetrics]:
    active = metrics or CacheMetrics()
    token = _metrics.set(active)
    try:
        yield active
    finally:
        _metrics.reset(token)


def _record(name: str) -> None:
    active = _metrics.get()
    if active is None:
        return
    with _lock:
        setattr(active, name, getattr(active, name) + 1)


def record_hit() -> None:
    _record("hits")


def record_miss() -> None:
    _record("misses")


def record_write() -> None:
    _record("writes")


def record_write_skipped() -> None:
    _record("write_skipped")


def record_stale_read() -> None:
    _record("stale_reads")


__all__ = [
    "CacheMetrics",
    "cache_metrics_scope",
    "record_hit",
    "record_miss",
    "record_stale_read",
    "record_write",
    "record_write_skipped",
]
