"""Local, atomic cache with per data-class TTLs."""
from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from tradingagents.contracts.cache import CacheEntry, CacheKey, TTLPolicy
from tradingagents.dataflows.files import locked, replace_file

from .metrics import (
    record_hit,
    record_miss,
    record_stale_read,
    record_write,
    record_write_skipped,
)


class CacheController:
    def __init__(self, root: str | Path, ttl: TTLPolicy | None = None):
        self.root = Path(root)
        self.ttl = ttl

    def _path(self, key: CacheKey) -> Path:
        digest = hashlib.sha256(key.model_dump_json().encode()).hexdigest()
        return self.root / f"{digest}.json"

    @contextmanager
    def _lock(self, path: Path):
        """Cross-process exclusive lock for a cache entry (Windows/POSIX)."""
        self.root.mkdir(parents=True, exist_ok=True)
        with locked(path):
            yield

    def get(self, key: CacheKey, *, now: datetime | None = None) -> CacheEntry | None:
        path = self._path(key)
        try:
            entry = CacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            record_miss()
            return None
        if entry.is_fresh(now):
            record_hit()
            return entry
        record_miss()
        return None

    def set(self, key: CacheKey, value: Any, provenance: dict[str, Any] | None = None,
            *, now: datetime | None = None) -> CacheEntry:
        now = now or datetime.now(UTC)
        policy = self.ttl or TTLPolicy.for_data_class(key.data_class)
        entry = CacheEntry(value=value, provenance=provenance or {}, created_at=now,
                           expires_at=now + timedelta(seconds=policy.seconds))
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        with self._lock(path):
            self._write_entry(path, entry)
        return entry

    def _write_entry(self, path: Path, entry: CacheEntry) -> None:
        def write(temp: str) -> None:
            with open(temp, "w", encoding="utf-8") as stream:
                stream.write(entry.model_dump_json())
                stream.flush()
                os.fsync(stream.fileno())

        if replace_file(path, write):
            record_write()
        else:
            record_write_skipped()

    def get_or_fetch(self, key: CacheKey, fetch_fn: Callable[[], Any],
                     provenance: dict[str, Any] | None = None) -> CacheEntry:
        path = self._path(key)
        with self._lock(path):
            hit = self.get(key)
            if hit is not None:
                return hit
            result = fetch_fn()
            result_provenance = provenance or {}
            if isinstance(result, tuple) and len(result) == 2:
                value, result_provenance = result
            else:
                value = result
            now = datetime.now(UTC)
            policy = self.ttl or TTLPolicy.for_data_class(key.data_class)
            entry = CacheEntry(value=value, provenance=result_provenance,
                               created_at=now, expires_at=now + timedelta(seconds=policy.seconds))
            self._write_entry(path, entry)
            return entry

    def get_stale(self, key: CacheKey) -> CacheEntry | None:
        """Return an expired value for explicit failure fallback only."""
        try:
            entry = CacheEntry.model_validate_json(
                self._path(key).read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return None
        record_stale_read()
        return entry
