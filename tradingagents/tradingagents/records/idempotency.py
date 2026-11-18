"""Idempotent decision records (REQ-INV-001).

A decision is identified by ``(ticker, trade_date, run_signature)``. Re-running
the same key (a retry, a duplicate job) must not create a second record; a run
with a different signature (profile/models changed) is a distinct version.

``record_id`` derives a stable key; ``IdempotentStore`` keeps a JSON index of
committed records beside the record tree and refuses to write a duplicate key.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from tradingagents.dataflows.files import locked, replace_file


def record_id(ticker: str, trade_date: str, run_signature: str = "") -> str:
    """Stable id for a decision: sha256 of the (ticker, date, signature) key."""
    key = f"{ticker.upper()}|{trade_date}|{run_signature}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class IdempotentStore:
    """A directory of versioned decision records with a de-duplicating index."""

    def __init__(self, root):
        self._root = Path(root)
        self._index_path = self._root / "index.json"
        self._root.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict[str, str]:
        if not self._index_path.exists():
            return {}
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def contains(self, rid: str) -> bool:
        return rid in self._load_index()

    def latest_for(self, ticker: str, trade_date: str) -> str | None:
        """The most recently written record id for a (ticker, date), if any."""
        prefix = f"{ticker.upper()}|{trade_date}|"
        latest = None
        for rid, key in self._load_index().items():
            if key.startswith(prefix):
                latest = rid
        return latest

    def store(self, ticker: str, trade_date: str, run_signature: str, files: Mapping[str, str]) -> tuple[str, bool]:
        """Record a decision atomically and idempotently.

        Returns ``(record_id, written)``. ``written`` is False when the same key
        was already recorded (a duplicate run): the existing record is kept and
        nothing is overwritten.
        """
        rid = record_id(ticker, trade_date, run_signature)
        with locked(self._index_path):
            index = self._load_index()
            if rid in index:
                return rid, False
            # Imported here to avoid a cycle and to keep the atomic primitive a
            # single import site.
            from tradingagents.records.atomic import write_record

            write_record(self._root / rid, files)
            index[rid] = f"{ticker.upper()}|{trade_date}|{run_signature}"
            replace_file(self._index_path, lambda temp: Path(temp).write_text(
                json.dumps(index, indent=2, sort_keys=True), encoding="utf-8"))
            return rid, True
