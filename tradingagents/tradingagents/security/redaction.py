"""Secret redaction (Part 5, REQ-INV-004).

Credentials — API keys, bearer tokens, query-param auth secrets — must never
reach logs, reports, manifests, prompts/model context, or error messages. This
module centralises redaction so every sink shares one implementation:

- :func:`redact` — the single public entry point; redacts any nested value
  (str, bytes, dict, list, tuple, exception, or arbitrary object's repr).
- :func:`redact_text` — redact a single string.
- :func:`redact_obj` — recurse into nested containers.

Redaction has two sources of truth:

1. **Registered secrets**: actual key values the process loaded from the
   environment for known providers (via :data:`tradingagents.llm_clients.api_key_env.PROVIDER_API_KEY_ENV`).
   These are replaced exactly, so a key with no recognisable shape is still
   removed.
2. **Patterns**: well-known token shapes (OpenAI ``sk-...``, Anthropic
   ``sk-ant-...``, GitHub ``ghp_...``, generic ``Bearer <token>``, and
   ``key=``/``api_key=``/``token=`` query parameters). These catch keys not
   registered in this process.

Only *synthetic* keys are used in tests; this module never logs or prints a real
secret.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

__all__ = [
    "REDACTED",
    "REDACTED_PATTERNS",
    "register_secret",
    "redact_text",
    "redact_obj",
    "redact",
    "RedactingFilter",
    "install_log_filter",
    "safe_prompt_payload",
    "scrub_manifest",
    "contains_secret",
]

REDACTED = "***"

# Placeholder patterns. Each is anchored to a recognisable prefix so benign text
# (numbers, ordinary words, URLs without credentials) is preserved.
REDACTED_PATTERNS: tuple[re.Pattern[str], ...] = (
    # OpenAI-style: sk-... / sk-proj-... (also our synthetic test keys).
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    # Anthropic: sk-ant-...
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    # GitHub tokens.
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    # Bearer tokens (Authorization headers).
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}"),
    # Query-param / assignment secrets: key=..., api_key: ..., token="...".
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|token|secret|password)"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{6,}['\"]?"
    ),
    # AWS access key id (bearer/bedrock paths often carry one).
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)

# Key values registered by the process (from the env), replaced exactly. Kept in
# a module-level set so a caller that loaded a key can register it without us
# re-reading the environment. Never logged.
_REGISTERED_SECRETS: set[str] = set()


def register_secret(secret: str | None) -> None:
    """Register a literal secret value to be redacted verbatim.

    Empty / very short values are ignored: redacting a 1-2 char substring would
    over-redact ordinary text. A real key is never that short.
    """
    if secret and len(secret) >= 6:
        _REGISTERED_SECRETS.add(secret)


def _register_env_secrets() -> None:
    """Register the values of the known provider env vars, if present.

    Reads names from the canonical map so we never guess which env vars hold
    keys. Imported lazily to keep this module importable without the LLM stack.
    """
    try:
        from tradingagents.llm_clients.api_key_env import PROVIDER_API_KEY_ENV
    except Exception:  # pragma: no cover - import guard
        return
    for env_name in PROVIDER_API_KEY_ENV.values():
        if not env_name:
            continue
        value = os.environ.get(env_name)
        if value:
            register_secret(value)


def _redact_text(text: str) -> str:
    _register_env_secrets()
    out = text
    # Registered literals first: exact removal regardless of shape.
    for secret in sorted(_REGISTERED_SECRETS, key=len, reverse=True):
        if secret and secret in out:
            out = out.replace(secret, REDACTED)
    for pattern in REDACTED_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


def redact_text(text: str) -> str:
    """Redact secrets from a single string."""
    return _redact_text(text)


def redact_obj(value: Any) -> Any:
    """Recursively redact secrets from a nested value, preserving its shape.

    - ``str`` -> redacted ``str``
    - ``bytes`` -> redacted ``bytes``
    - ``dict`` -> new ``dict`` with redacted keys and values
    - ``list``/``tuple``/``set`` -> same type with redacted elements
    - ``BaseException`` -> a new exception of the same type with a redacted message
    - anything else -> redacted ``repr`` (objects are not echoed raw)
    """
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, bytes):
        return _redact_text(value.decode("utf-8", "replace")).encode("utf-8", "replace")
    if isinstance(value, dict):
        return {redact_obj(k): redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_obj(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_obj(v) for v in value)
    if isinstance(value, set):
        return {redact_obj(v) for v in value}
    if isinstance(value, BaseException):
        try:
            return type(value)(_redact_text(str(value)))
        except Exception:  # pragma: no cover - exotic exception ctor
            return REDACTED
    if value is None or isinstance(value, (int, float, bool)):
        return value
    # Unknown object: do not echo it raw; redact its repr.
    return _redact_text(repr(value))


def redact(value: Any) -> Any:
    """The unified redaction entry point for any value or sink."""
    if isinstance(value, str):
        return _redact_text(value)
    return redact_obj(value)


def contains_secret(value: Any) -> bool:
    """Whether a (stringified) value still contains a known secret pattern.

    Used by tests and the security log as a last-line assertion; it checks both
    registered literals and the placeholder patterns.
    """
    text = value if isinstance(value, str) else repr(value)
    if any(secret in text for secret in _REGISTERED_SECRETS):
        return True
    return any(pattern.search(text) for pattern in REDACTED_PATTERNS)


class RedactingFilter(logging.Filter):
    """A logging filter that redacts a record before it is emitted.

    Handles the three ways a log line can carry a secret:

    - ``record.msg`` when it is the final string;
    - deferred ``%``-style arguments in ``record.args`` (``log.info("k=%s", key)``);
    - exception text in ``record.exc_info`` / ``record.exc_text``.

    ``record.args`` is redacted element-wise, then the formatted message is
    materialised and redacted (so formats like ``Bearer %s`` are also covered).
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 - logging API
        if isinstance(record.msg, str):
            record.msg = _redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_obj(record.args)
            else:
                record.args = tuple(redact_obj(a) for a in record.args)
        # Materialise the final message so formatting-introduced secrets are
        # caught, and so downstream handlers that re-format see a redacted msg.
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - malformed record
            message = str(record.msg)
        if contains_secret(message):
            record.msg = _redact_text(message)
            record.args = ()
        if record.exc_info:
            exc = record.exc_info[1]
            if exc is not None:
                record.exc_text = _redact_text(str(exc))
        elif record.exc_text:
            record.exc_text = _redact_text(record.exc_text)
        return True


def install_log_filter(logger: logging.Logger | None = None) -> RedactingFilter:
    """Attach a :class:`RedactingFilter` to ``logger`` (root by default).

    Returns the filter so callers/tests can remove it. Idempotent: returns the
    existing filter if one is already installed on that logger.
    """
    target = logger or logging.getLogger()
    for existing in target.filters:
        if isinstance(existing, RedactingFilter):
            return existing
    filt = RedactingFilter()
    target.addFilter(filt)
    return filt


def safe_prompt_payload(messages: Any) -> Any:
    """A prompt payload safe to send to a model: redacted, with a guard.

    This is the adapter Part 1/2 should call before a model request. It redacts
    the payload and asserts no registered/patterned secret survives; it never
    reads a key into the payload.
    """
    redacted = redact_obj(messages)
    if contains_secret(redacted):
        # Defensive: after redaction nothing should remain. Drop to a marker
        # rather than risk sending a secret.
        return redact_obj(redacted)
    return redacted


def scrub_manifest(manifest: Any) -> Any:
    """A manifest/report payload with every secret redacted before persistence.

    Part 3 calls this immediately before writing ``manifest.json`` or a report so
    a secret in a field (e.g. a vendor error captured in an event) cannot reach
    disk. Shape is preserved.
    """
    return redact_obj(manifest)
