"""Security event log (Part 5, REQ-SEC-001 acceptance line 5).

Every detection, sanitisation, validation failure and tool rejection is recorded
as a :class:`SecurityEvent` with a machine-readable ``kind`` and a human
``reason``. The event is **redacted before it is stored**, so a security log can
itself never become a secret-leak sink.

The log is in-memory and append-only by default, so it is deterministic and
offline-testable. Production can attach a drain (e.g. Part 3's manifest
``security_events`` list) via :func:`drain_events`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .redaction import redact_obj

__all__ = [
    "SecurityEvent",
    "EventKind",
    "SecurityEventLog",
    "get_event_log",
    "log_event",
    "drain_events",
    "reset_event_log",
]

logger = logging.getLogger(__name__)


class EventKind:
    """Stable event kinds (one per detection/validation/tool outcome)."""

    INPUT_SANITIZED = "input_sanitized"
    INPUT_DROPPED = "input_dropped"
    OUTPUT_REJECTED = "output_rejected"
    TOOL_REJECTED = "tool_rejected"
    TOOL_ALLOWED = "tool_allowed"


@dataclass(frozen=True)
class SecurityEvent:
    """A single security event; all free text is redacted before storage."""

    kind: str
    reason: str
    detail: Any = None
    at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict:
        return {"kind": self.kind, "reason": self.reason,
                "detail": self.detail, "at": self.at}


class SecurityEventLog:
    """An append-only, in-memory, redacted event log."""

    def __init__(self) -> None:
        self._events: list[SecurityEvent] = []

    def record(self, kind: str, reason: str, detail: Any = None) -> SecurityEvent:
        event = SecurityEvent(kind=kind, reason=redact_obj(reason),
                              detail=redact_obj(detail))
        self._events.append(event)
        return event

    def events(self) -> list[SecurityEvent]:
        return list(self._events)

    def drain(self) -> list[dict]:
        """Return the events then clear them (used to hand off to a manifest)."""
        out = [e.as_dict() for e in self._events]
        self._events.clear()
        return out

    def count(self, kind: str | None = None) -> int:
        if kind is None:
            return len(self._events)
        return sum(1 for e in self._events if e.kind == kind)


_DEFAULT_LOG = SecurityEventLog()


def get_event_log() -> SecurityEventLog:
    """The process-wide event log (tests may :func:`reset_event_log`)."""
    return _DEFAULT_LOG


def reset_event_log() -> None:
    """Clear the process-wide event log (for test isolation)."""
    _DEFAULT_LOG.drain()


def log_event(kind: str, reason: str, detail: Any = None,
              event_log: SecurityEventLog | None = None) -> SecurityEvent:
    """Record ``kind``/``reason`` on ``event_log`` (default: process-wide)."""
    target = event_log or _DEFAULT_LOG
    event = target.record(kind, reason, detail)
    # Mirror to the stdlib logger; a RedactingFilter (if installed) scrubs it,
    # and the message here is already redacted.
    logger.debug("security_event kind=%s reason=%s", event.kind, event.reason)
    return event


def drain_events(event_log: SecurityEventLog | None = None) -> list[dict]:
    """Drain events as plain dicts for a manifest / report field."""
    return (event_log or _DEFAULT_LOG).drain()
