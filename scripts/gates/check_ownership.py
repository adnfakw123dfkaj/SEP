"""Ownership gate (G7) — a claimed Part's tests must not skip or fail.

Each Part is claimed by editing ``test-cases/ownership.yaml`` (``enabled: true``
plus ``owner``) in the developer's branch. Once claimed, that Part's tests are a
commitment: any ``skipped`` outcome (the "awaiting implementation" guard) or any
failure blocks the change. Unclaimed Parts may skip freely — their work has not
started and must not burden other branches.

This check reads the ownership registry and the per-test outcomes the workflow
collected, and returns a GateResult. It is pure and offline.
"""

from __future__ import annotations

from common import GateResult, Violation

PASS = "passed"
SKIP = "skipped"
FAIL = "failed"
ERROR = "error"


def _normalize(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _owned_outcomes(part: dict, outcomes: dict[str, str]) -> dict[str, str]:
    """The outcomes belonging to a Part's test files (any test id under them)."""
    prefixes = [_normalize(p) for p in part.get("tests", [])]
    owned: dict[str, str] = {}
    for test_id, outcome in outcomes.items():
        nid = _normalize(test_id)
        if any(nid.startswith(p) or f"/{p}" in nid for p in prefixes):
            owned[test_id] = outcome
    return owned


def check(ownership: dict, outcomes: dict[str, str]) -> GateResult:
    """Evaluate the ownership gate.

    Args:
        ownership: the parsed ``ownership.yaml`` (a ``parts`` mapping).
        outcomes: test id -> outcome for the current run.
    """
    result = GateResult(gate="G7")
    parts = (ownership or {}).get("parts") or {}

    for name, part in parts.items():
        if not part.get("enabled"):
            continue  # unclaimed: its skips are allowed
        owned = _owned_outcomes(part, outcomes)
        if not owned:
            result.violations.append(
                Violation("claimed part has no test outcomes", f"{name} (tests not run?)")
            )
            continue
        for test_id, outcome in owned.items():
            if outcome == SKIP:
                result.violations.append(
                    Violation("claimed part test skipped", f"{name}: {test_id}")
                )
            elif outcome in (FAIL, ERROR):
                result.violations.append(
                    Violation(f"claimed part test {outcome}", f"{name}: {test_id}")
                )
    return result
