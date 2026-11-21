"""Keep redirected CLI output writable when the Windows code page cannot encode it."""

from __future__ import annotations

import sys
from collections.abc import Iterable


def ensure_utf8_output(streams: Iterable | None = None) -> None:
    """Reconfigure text streams to UTF-8 where the platform allows it."""
    for stream in streams if streams is not None else (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            continue
