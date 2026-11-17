"""Gate 3 — Schema gate (PDF §6.3).

The requirements registry validates against its JSON schema.

This check deliberately does not pull in the ``jsonschema`` package as a hard
dependency: it implements exactly the subset the registry needs (required keys,
enum membership, nested fit-criterion object, unique ids). That keeps the gate
runnable in any CI image and fully unit-testable offline. The companion
``docs/req/req-schema.json`` is the documented contract; this module is its
executable mirror for the CI check.
"""

from __future__ import annotations

from common import GateResult, Violation

# Requirement types from the project's type catalogue (Appendix M subset used).
ALLOWED_TYPES = {
    "REQ-FR", "REQ-INV", "REQ-QUAL", "REQ-PER", "REQ-COST", "REQ-GOV", "REQ-SEC",
    "REQ-UNCLEAR", "ARCH-EA",
}
ALLOWED_PRIORITY = {"Must", "Should", "Could", "Won't"}

REQUIRED_TOP_KEYS = ("id", "type", "priority", "statement", "fit_criterion")
FIT_CRITERION_KEYS = ("metric", "threshold", "verification")


def _type_prefix(entry_id: str) -> str:
    """The type an id implies, e.g. ``REQ-FR-001`` -> ``REQ-FR``."""
    parts = entry_id.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else ""


def validate_entry(entry: dict, index: int) -> list[Violation]:
    """All violations of one registry entry."""
    violations: list[Violation] = []
    where = entry.get("id") or f"entry[{index}]"

    for key in REQUIRED_TOP_KEYS:
        if key not in entry or entry[key] in (None, ""):
            violations.append(Violation("missing key", f"{where}: {key}"))

    entry_id = entry.get("id")
    if entry_id:
        if _type_prefix(entry_id) != entry.get("type"):
            violations.append(
                Violation("id/type mismatch", f"{where}: prefix implies {_type_prefix(entry_id)!r}, type is {entry.get('type')!r}")
            )
        if entry.get("type") not in ALLOWED_TYPES:
            violations.append(Violation("unknown type", f"{where}: {entry.get('type')!r}"))

    if entry.get("priority") not in ALLOWED_PRIORITY:
        violations.append(Violation("priority out of MoSCoW set", f"{where}: {entry.get('priority')!r}"))

    fit = entry.get("fit_criterion")
    if isinstance(fit, dict):
        for key in FIT_CRITERION_KEYS:
            if not fit.get(key):
                violations.append(Violation("missing fit-criterion field", f"{where}: fit_criterion.{key}"))
    elif "fit_criterion" in entry:
        violations.append(Violation("fit_criterion not an object", where))

    return violations


def check(registry: dict | list) -> GateResult:
    """Validate a requirements registry.

    The registry may be a mapping with an ``entries`` list or a bare list of
    entries. Every entry must carry the required keys, a type matching its id
    prefix, a MoSCoW priority, and a complete fit criterion; ids must be unique.
    """
    result = GateResult(gate="G3")
    entries = registry.get("entries") if isinstance(registry, dict) else registry
    if not isinstance(entries, list):
        result.violations.append(Violation("registry is not a list of entries"))
        return result

    seen: dict[str, int] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            result.violations.append(Violation("entry is not an object", f"entry[{index}]"))
            continue
        for violation in validate_entry(entry, index):
            result.violations.append(violation)
        entry_id = entry.get("id")
        if entry_id:
            if entry_id in seen:
                result.violations.append(
                    Violation("duplicate id", f"{entry_id} at entries {seen[entry_id]} and {index}")
                )
            else:
                seen[entry_id] = index

    return result
