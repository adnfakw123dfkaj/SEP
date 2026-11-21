"""Local, atomic cache with per data-class TTLs."""
from __future__ import annotations

import hashlib
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from tradingagents.contracts.cache import CacheEntry, CacheKey, TTLPolicy


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
        lock_path = path.with_suffix(path.suffix + ".lock")
        with lock_path.open("a+b") as lock_file:
            if os.name == "nt":
                import msvcrt
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.seek(0)
                    lock_file.write(b"0")
                    lock_file.flush()
                lock_file.seek(0)
                while True:
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.01)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def get(self, key: CacheKey, *, now: datetime | None = None) -> CacheEntry | None:
        path = self._path(key)
        try:
            entry = CacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return entry if entry.is_fresh(now) else None

    def set(self, key: CacheKey, value: Any, provenance: dict[str, Any] | None = None,
            *, now: datetime | None = None) -> CacheEntry:
        now = now or datetime.now(timezone.utc)
        policy = self.ttl or TTLPolicy.for_data_class(key.data_class)
        entry = CacheEntry(value=value, provenance=provenance or {}, created_at=now,
                           expires_at=now + timedelta(seconds=policy.seconds))
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        with self._lock(path):
            self._write_entry(path, entry)
        return entry

    def _write_entry(self, path: Path, entry: CacheEntry) -> None:
        fd, name = tempfile.mkstemp(dir=self.root, prefix=".cache-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(entry.model_dump_json())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)

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
            now = datetime.now(timezone.utc)
            policy = self.ttl or TTLPolicy.for_data_class(key.data_class)
            entry = CacheEntry(value=value, provenance=result_provenance,
                               created_at=now, expires_at=now + timedelta(seconds=policy.seconds))
            self._write_entry(path, entry)
            return entry

    def get_stale(self, key: CacheKey) -> CacheEntry | None:
        """Return an expired value for explicit failure fallback only."""
        try:
            return CacheEntry.model_validate_json(self._path(key).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
