"""Model-output validation before it becomes state (Part 5, REQ-SEC-001).

Model output is untrusted. Before any field becomes part of the run state it is
validated against a declarative schema whose supported vocabulary is deliberately
small and explicit — this is **not** a claim to implement full JSON Schema:

==========================  ====================================================
keyword                     meaning
==========================  ====================================================
``type``                    ``object`` / ``array`` / ``string`` / ``number`` /
                            ``integer`` / ``boolean`` / ``null``
``properties``              per-key sub-schema (object)
``required``                keys that must be present (object)
``enum``                    value must be one of the listed values
``items``                   element sub-schema (array)
``refs``                    list of field names whose string values must be ids
                            that appear in a supplied reference set (referential
                            integrity, e.g. evidence ids cited by the report)
==========================  ====================================================

A field failing the type/enum/ref checks, or a required field that is missing,
makes the whole output **invalid**: the caller must drop it (not store it) and a
``security_event`` is logged with the reason. The validator never mutates or
"repairs" the input.

Use an existing mature validator when a full JSON Schema is needed; this module
covers exactly the structure/type/enum/reference checks the requirement names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .security_log import EventKind, SecurityEventLog, get_event_log, log_event

__all__ = ["ValidationResult", "validate_output"]

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    # bool is a subclass of int in Python; handle integer/number explicitly.
    "integer": int,
    "number": (int, float),
    "null": type(None),
}


@dataclass
class ValidationResult:
    """Outcome of validating one model output against a schema."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    value: Any = None  # the original value when ok; the dropped payload is None

    @property
    def rejected(self) -> bool:
        return not self.ok


def _type_ok(expected: str, value: Any) -> bool:
    py = _TYPE_MAP.get(expected)
    if py is None:
        return False
    if expected in ("integer", "number") and isinstance(value, bool):
        # True/False must not pass as an integer/number.
        return False
    return isinstance(value, py)


def _check(schema: dict, value: Any, path: str, errors: list[str],
           refs: frozenset[str] | None) -> None:
    expected = schema.get("type")
    if expected is not None and not _type_ok(expected, value):
        errors.append(f"{path or '$'}: expected {expected}, got {type(value).__name__}")
        return

    if "enum" in schema:
        allowed = schema["enum"]
        if value not in allowed:
            errors.append(f"{path or '$'}: {value!r} not in enum {allowed!r}")
            return

    if isinstance(value, str) and refs is not None and schema.get("ref") and value not in refs:
        errors.append(f"{path or '$'}: reference {value!r} not found")
        return

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path or '$'}: missing required {key!r}")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                _check(sub, value[key], f"{path}.{key}" if path else key, errors, refs)

    if isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(value):
                _check(item_schema, item, f"{path}[{i}]", errors, refs)


def _schema_uses_refs(schema: dict) -> bool:
    """Whether any node in ``schema`` marks a field with ``ref: True``."""
    if not isinstance(schema, dict) or not schema:
        return False
    if schema.get("ref"):
        return True
    items = schema.get("items")
    if isinstance(items, dict) and items and _schema_uses_refs(items):
        return True
    props = schema.get("properties")
    if isinstance(props, dict):
        return any(_schema_uses_refs(sub) for sub in props.values())
    return False


def validate_output(
    value: Any,
    schema: dict,
    *,
    references: set[str] | frozenset[str] | None = None,
    event_log: SecurityEventLog | None = None,
) -> ValidationResult:
    """Validate ``value`` against ``schema`` before it may become state.

    Args:
        value: the model's parsed output (dict/list/etc.).
        schema: the small schema vocabulary described in the module docstring.
        references: the set of valid ids a ``ref``-marked field may cite. **If
            the schema uses ``ref`` and this is ``None``, validation fails closed
            with a configuration error** — an omitted reference set must never
            silently pass a reference check. An empty set means "no id is valid".
        event_log: where to record the rejection (default: process-wide).

    Returns:
        :class:`ValidationResult`. On failure ``ok`` is False, ``value`` is
        ``None`` (the caller must drop it), ``errors`` lists every reason, and a
        ``security_event`` of kind ``output_rejected`` is logged.
    """
    errors: list[str] = []

    # Fail closed: a schema that checks references but was given no reference
    # set is a configuration error, not a pass.
    if _schema_uses_refs(schema) and references is None:
        message = "missing references configuration: schema uses ref=True but no references were provided"
        target = event_log or get_event_log()
        log_event(EventKind.OUTPUT_REJECTED, "schema:" + message, event_log=target)
        return ValidationResult(ok=False, errors=[message], value=None)

    ref_set = frozenset(references) if references is not None else None
    _check(schema, value, "", errors, ref_set)

    if errors:
        target = event_log or get_event_log()
        log_event(EventKind.OUTPUT_REJECTED, "schema:" + "; ".join(errors[:5]),
                  event_log=target)
        return ValidationResult(ok=False, errors=errors, value=None)

    return ValidationResult(ok=True, errors=[], value=value)
