"""Security components (Part 5, REQ-SEC-001 / REQ-INV-004).

This package holds the untrusted-input / untrusted-output defences and the
secret-redaction sink shared by the rest of the pipeline:

- :mod:`tradingagents.security.sanitize` — sanitise untrusted text before it
  enters a prompt (control chars, instruction patterns, delimiters, length).
- :mod:`tradingagents.security.validate_output` — validate model output
  structure/values before it becomes state.
- :mod:`tradingagents.security.tool_guard` — reject unauthorised tool calls
  before they execute.
- :mod:`tradingagents.security.security_log` — record detection/validation/
  rejection events (redacted) for audit.
- :mod:`tradingagents.security.redaction` — keep secrets out of every sink.

The modules are independent of the composition root: Part 1 wires them into the
graph; Part 3 wires the redaction into manifest/report writes. See
``docs/part5-integration.md``.
"""

from __future__ import annotations

from .redaction import (
    REDACTED,
    RedactingFilter,
    contains_secret,
    install_log_filter,
    redact,
    redact_obj,
    redact_text,
    register_secret,
    safe_prompt_payload,
    scrub_manifest,
)
from .sanitize import (
    CLOSE_DELIM,
    OPEN_DELIM,
    SanitizedText,
    is_suspicious,
    sanitize,
    sanitize_detailed,
)
from .security_log import (
    EventKind,
    SecurityEvent,
    SecurityEventLog,
    drain_events,
    get_event_log,
    log_event,
    reset_event_log,
)
from .tool_guard import (
    RoleToolGuard,
    ToolGuard,
    UnauthorizedToolCall,
)
from .validate_output import ValidationResult, validate_output

__all__ = [
    # redaction
    "REDACTED",
    "RedactingFilter",
    "contains_secret",
    "install_log_filter",
    "redact",
    "redact_obj",
    "redact_text",
    "register_secret",
    "safe_prompt_payload",
    "scrub_manifest",
    # sanitize
    "CLOSE_DELIM",
    "OPEN_DELIM",
    "SanitizedText",
    "is_suspicious",
    "sanitize",
    "sanitize_detailed",
    # security log
    "EventKind",
    "SecurityEvent",
    "SecurityEventLog",
    "drain_events",
    "get_event_log",
    "log_event",
    "reset_event_log",
    # tool guard
    "RoleToolGuard",
    "ToolGuard",
    "UnauthorizedToolCall",
    # output validation
    "ValidationResult",
    "validate_output",
]
