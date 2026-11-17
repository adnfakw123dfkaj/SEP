"""Gate 3 — Schema gate (PDF §6.3).

The requirements registry validates against its JSON schema.

This check implements the subset the registry needs as executable code (so it runs
in any CI image and is unit-testable offline). The documented contract is
``docs/req/req-schema.json``; this module is its executable mirror.

Registry shape (v1.0.1):

    requirements:
      - id: REQ-FR-001
        type: functional            # lowercase type name
        priority: must              # lowercase MoSCoW
        statement: ...
        fit_criterion:              # a LIST of metric/threshold/verification
          - {metric: ..., threshold: ..., verification: ...}
        ...

A bare list of entries (no ``requirements`` key) is also accepted.
"""

from __future__ import annotations

from common import GateResult, Violation

# Requirement type name -> the id prefix it must carry.
TYPE_TO_PREFIX = {
    "functional": "REQ-FR",
    "invariant": "REQ-INV",
    "quality": "REQ-QUAL",
    "performance": "REQ-PER",
    "cost": "REQ-COST",
    "governance": "REQ-GOV",
    "security": "REQ-SEC",
    "unclear": "REQ-UNCLEAR",
    "architectural_constraint": "ARCH-EA",
}
ALLOWED_PRIORITY = {"must", "should", "could", "wont"}

REQUIRED_TOP_KEYS = ("id", "type", "priority", "statement", "fit_criterion")
FIT_CRITERION_KEYS = ("metric", "threshold", "verification")


def _entries(registry) -> list | None:
    if isinstance(registry, dict) and "requirements" in registry:
        return registry["requirements"]
    if isinstance(registry, dict) and "entries" in registry:
        return registry["entries"]
    if isinstance(registry, list):
        return registry
    return None


def _type_prefix(entry_id: str) -> str:
    parts = entry_id.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else ""


def validate_entry(entry: dict, index: int) -> list[Violation]:
    violations: list[Violation] = []
    where = entry.get("id") or f"entry[{index}]"

    for key in REQUIRED_TOP_KEYS:
        if key not in entry or entry[key] in (None, "", [], {}):
            violations.append(Violation("missing key", f"{where}: {key}"))

    entry_id, entry_type = entry.get("id"), entry.get("type")
    if entry_id and entry_type:
        expected = TYPE_TO_PREFIX.get(entry_type)
        if expected is None:
            violations.append(Violation("unknown type", f"{where}: {entry_type!r}"))
        elif _type_prefix(entry_id) != expected:
            violations.append(
                Violation(
                    "id/type mismatch",
                    f"{where}: type {entry_type!r} needs prefix {expected!r}, id has {_type_prefix(entry_id)!r}",
                )
            )

    if entry.get("priority") not in ALLOWED_PRIORITY:
        violations.append(Violation("priority out of MoSCoW set", f"{where}: {entry.get('priority')!r}"))

    fit = entry.get("fit_criterion")
    if isinstance(fit, list):
        if not fit:
            violations.append(Violation("empty fit_criterion", where))
        for j, crit in enumerate(fit):
            if not isinstance(crit, dict):
                violations.append(Violation("fit_criterion item not an object", f"{where}[{j}]"))
                continue
            for key in FIT_CRITERION_KEYS:
                if not crit.get(key):
                    violations.append(Violation("missing fit-criterion field", f"{where}[{j}].{key}"))
    elif "fit_criterion" in entry:
        violations.append(Violation("fit_criterion not a list", where))

    return violations


def check(registry: dict | list) -> GateResult:
    """Validate a requirements registry (see module docstring for the shape)."""
    result = GateResult(gate="G3")
    entries = _entries(registry)
    if entries is None or not isinstance(entries, list):
        result.violations.append(Violation("registry has no requirements list"))
        return result

    seen: dict[str, int] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            result.violations.append(Violation("entry is not an object", f"entry[{index}]"))
            continue
        result.violations.extend(validate_entry(entry, index))
        entry_id = entry.get("id")
        if entry_id:
            if entry_id in seen:
                result.violations.append(
                    Violation("duplicate id", f"{entry_id} at entries {seen[entry_id]} and {index}")
                )
            else:
                seen[entry_id] = index

    return result
