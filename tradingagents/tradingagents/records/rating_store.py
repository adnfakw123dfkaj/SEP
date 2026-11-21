"""File-backed rating store for the Part 5 commit gate."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class FileRatingStore:
    """Persist committed ratings as one atomic JSON file per decision id."""

    def __init__(self, root: str | Path):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, decision_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in decision_id)
        return self._root / f"{safe}.json"

    def read(self, decision_id: str) -> dict[str, Any] | None:
        path = self._path(decision_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            return {"rating": None}
        return data if isinstance(data, dict) else {"rating": None}

    def write(self, decision_id: str, record: dict[str, Any]) -> None:
        path = self._path(decision_id)
        fd, temp_name = tempfile.mkstemp(dir=self._root, prefix=".rating-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(record, stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        finally:
            Path(temp_name).unlink(missing_ok=True)
