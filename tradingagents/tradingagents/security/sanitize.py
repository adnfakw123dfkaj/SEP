"""Untrusted text sanitisation (Part 5, REQ-SEC-001).

News, social posts and user input are untrusted. Before such text enters a
prompt it is sanitised here:

- C0/C1 control characters (except tab/newline) are removed.
- Prompt-injection *shapes* are detected: instruction override, role hijack,
  tool/function-call injection, and delimiter-escape attempts. A detected line
  is **dropped** (not merely warned about) and the drop is logged.
- The surviving text is wrapped in a delimiter so the model can tell data from
  instructions. Any forged closing delimiter in the input is neutralised, and
  re-sanitising already-wrapped text does not double-wrap or break out.
- Length is bounded; over-long text is truncated with an explicit marker.

Ordinary numbers, URLs and factual words are preserved: detection targets
instruction-like *structures*, not the presence of words like "buy" or "sell".

Public API:

- :func:`sanitize(text) -> str` — the simple entry point required by callers;
  returns the delimited, sanitised text (safe to place in a prompt).
- :func:`sanitize_detailed(text) -> SanitizedText` — the full result with
  ``text`` (same as :func:`sanitize`), ``dropped`` (bool), ``events`` and the
  ``retained`` (undelimited) text, for callers/tests that need the detail.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .security_log import EventKind, SecurityEventLog, get_event_log, log_event

__all__ = [
    "SanitizedText",
    "sanitize",
    "sanitize_detailed",
    "is_suspicious",
    "OPEN_DELIM",
    "CLOSE_DELIM",
]

OPEN_DELIM = "<untrusted>"
CLOSE_DELIM = "</untrusted>"

DEFAULT_MAX_LEN = 8_000

# C0/C1 controls except \t \n \r.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Instruction-override / role-hijack / tool-call shapes. These target the
# *structure* of an injection, not benign mentions of a company or a rating.
_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # "ignore (all) previous instructions", "disregard the above"
    ("instruction_override", re.compile(
        r"(?i)\b(ignore|disregard|forget|override|bypass)\b[^.\n]{0,40}"
        r"\b(previous|prior|above|earlier|all|any|your|the)\b[^.\n]{0,30}"
        r"\b(instruction|instructions|prompt|prompts|rules?|directions?|"
        r"debate|analysis|analyst|guidance|guidelines)\b")),
    # "new instructions:", "system override:", "obey the following"
    ("override_shorthand", re.compile(
        r"(?i)(\bnew\s+instructions?\b|\bsystem\s+override\b|"
        r"\bobey\s+(the\s+)?following\b|\bfrom\s+now\s+on\b|"
        r"\bonly\s+source\s+of\s+truth\b)")),
    # "you are now ...", "act as ...", "reveal your system prompt",
    # "developer mode", "jailbreak". A bare "system prompt" is a legitimate
    # security term, so it only counts when paired with an extract/obey verb.
    ("role_hijack", re.compile(
        r"(?i)(\byou are now\b|\bact as\b|\bpretend to be\b|"
        r"\b(print|reveal|show|repeat|output|ignore|override|leak)\b[^.\n]{0,20}"
        r"\bsystem prompt\b|"
        r"\bdeveloper mode\b|\bjailbreak\b|\bDAN\b)")),
    # "new instructions:" / "### system:" / "assistant:" role markers
    ("role_marker", re.compile(
        r"(?im)^\s*(#{1,6}\s*)?(system|assistant|developer|tool)\s*:")),
    # A role marker embedded mid-text ("news text system: ...") and explicit
    # "follow these instructions" phrasing.
    ("role_marker_inline", re.compile(
        r"(?i)(\b(system|assistant|developer)\s*:\s*(now|you|ignore|follow|obey)\b|"
        r"\bfollow\s+(only\s+)?(these|my|the\s+following)\s+instructions?\b)")),
    # Tool/function-call injection.
    ("tool_call_injection", re.compile(
        r"(?i)(\bcall\s+(the\s+)?(tool|function)\b|"
        r"\bexecute\s+(the\s+)?(tool|function|command|shell)\b|"
        r"<\|?\s*(tool_call|function_call)\s*\|?>|"
        r"\btool_call\s*\(|\bfunction_call\s*\()")),
    # Delimiter escape: attempt to close/forge our trust boundary.
    ("delimiter_escape", re.compile(
        r"(?i)(</?\s*untrusted\s*>|</?\s*system\s*>|<\|im_(start|end)\|>)")),
)


@dataclass
class SanitizedText:
    """The detailed outcome of sanitising one untrusted text."""

    text: str                       # delimited text safe for a prompt
    retained: str                   # undelimited sanitised text (facts kept)
    dropped: bool
    events: list[dict] = field(default_factory=list)
    truncated: bool = False

    def __str__(self) -> str:       # so sanitize() can return it transparently
        return self.text


def _normalise(text: str) -> str:
    # NFKC folds fullwidth/confusable forms so an injection written in fullwidth
    # punctuation is still recognised.
    return unicodedata.normalize("NFKC", text)


def _strip_controls(text: str) -> str:
    return _CONTROL_RE.sub("", text)


def _matching_kinds(text: str) -> list[str]:
    kinds = []
    for name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            kinds.append(name)
    return kinds


def is_suspicious(text: str) -> bool:
    """Whether ``text`` contains an injection-shaped structure.

    If ``text`` is already wrapped by :func:`sanitize` (our own delimiters), the
    wrapper is unwrapped first, so our own boundary is not mistaken for a forged
    one.
    """
    cleaned = _strip_controls(_normalise(text or ""))
    return bool(_matching_kinds(_unwrap(cleaned)))


def _neutralise_delimiters(text: str) -> str:
    # Defang any forged delimiters so data cannot pretend to close our wrapper.
    text = re.sub(r"(?i)</?\s*untrusted\s*>", "[delimiter]", text)
    text = re.sub(r"(?i)</?\s*system\s*>", "[delimiter]", text)
    text = re.sub(r"(?i)<\|im_(start|end)\|>", "[delimiter]", text)
    return text


def sanitize_detailed(
    text: str,
    *,
    max_len: int = DEFAULT_MAX_LEN,
    event_log: SecurityEventLog | None = None,
) -> SanitizedText:
    """Sanitise one untrusted text and return the detail (see module docs).

    A text containing an injection structure is *dropped*: the returned
    ``text``/``retained`` is empty and ``dropped`` is True. Benign text is
    cleaned, delimiter-neutralised, bounded, and wrapped.
    """
    target_log = event_log or get_event_log()
    raw = text or ""

    normalised = _normalise(raw)
    cleaned = _strip_controls(normalised)
    # If the input is our own wrapper (re-sanitising), unwrap it first so the
    # wrapper's own delimiters are not mistaken for a forged escape.
    cleaned = _unwrap(cleaned)

    kinds = _matching_kinds(cleaned)
    if kinds:
        for kind in kinds:
            log_event(EventKind.INPUT_DROPPED, f"injection:{kind}",
                      detail={"preview": cleaned[:200]}, event_log=target_log)
        return SanitizedText(text="", retained="", dropped=True,
                             events=[e.as_dict() for e in target_log.events()])

    retained = _neutralise_delimiters(cleaned).strip()
    truncated = False
    if len(retained) > max_len:
        retained = retained[:max_len].rstrip() + " […truncated]"
        truncated = True

    # Wrap once. If the input was already wrapped (re-sanitising), unwrap first
    # so we neither double-wrap nor nest.
    retained = _unwrap(retained)
    wrapped = f"{OPEN_DELIM}\n{retained}\n{CLOSE_DELIM}"

    log_event(EventKind.INPUT_SANITIZED, "clean",
              detail={"truncated": truncated}, event_log=target_log)
    return SanitizedText(text=wrapped, retained=retained, dropped=False,
                         events=[e.as_dict() for e in target_log.events()],
                         truncated=truncated)


def _unwrap(text: str) -> str:
    """Strip an outer OPEN/CLOSE delim pair so re-sanitising is idempotent."""
    stripped = text.strip()
    if stripped.startswith(OPEN_DELIM) and stripped.endswith(CLOSE_DELIM):
        inner = stripped[len(OPEN_DELIM):-len(CLOSE_DELIM)]
        return inner.strip()
    return text


def sanitize(text: str, *, max_len: int = DEFAULT_MAX_LEN,
             event_log: SecurityEventLog | None = None) -> str:
    """Sanitise ``text`` and return prompt-safe, delimited text.

    The simple entry point: returns a ``str``. An injection-shaped text yields
    ``""`` (dropped); use :func:`sanitize_detailed` when you need to know that
    it was dropped and why.
    """
    return sanitize_detailed(text, max_len=max_len, event_log=event_log).text
