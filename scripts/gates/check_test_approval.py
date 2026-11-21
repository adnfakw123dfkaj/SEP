"""Gate 1 — Test approval gate (PDF §6.1).

No code change merges unless the tests for the change were approved *before*
implementation began.

Approval evidence is a committed record with fields ``change_id``, ``tests``
(list of test paths it approves), ``approved_by`` and ``approved_at`` (ISO-8601).
The gate is given the changed files and the first implementation commit time (the
earliest non-test code change), and checks:

- if only tests changed (no production code), the gate does not apply;
- otherwise an approval must exist;
- it must cover every changed test file;
- its ``approved_at`` must be earlier than the first implementation commit.
"""

from __future__ import annotations

import re
from datetime import datetime

from common import GateResult, Violation

# A path is a test path when it lives under a tests/ dir or names a test module.
_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]*\.py$|_test\.py$")
# Trees that hold non-code (docs, data, config) — never "implementation" for G1.
_NON_CODE_PREFIXES = ("docs/", "test-cases/", ".github/")
_PROMPT_PREFIXES = ("prompts/",)
# Gate-infrastructure maintenance (the gate's own scripts, tests, and CI wiring)
# is not application behaviour and has no "tests approved before implementation"
# phase — it is reviewed like any code change, but G1 does not apply to it.
_GATE_INFRA_PREFIXES = ("scripts/gates/", "tests/gates/")


def is_test_path(path: str) -> bool:
    return bool(_TEST_PATH.search(path))


def is_gate_infrastructure_path(path: str) -> bool:
    normalized = path.lstrip("./")
    return any(normalized.startswith(p) for p in _GATE_INFRA_PREFIXES)


def is_code_path(path: str) -> bool:
    """Whether ``path`` is production source code that needs a test approval.

    Only real source files count: a ``.py`` file that is not a test, under the
    package or the scripts, plus prompt files. Docs, data (yaml/json), markdown
    and CI config are not "code" for this gate — touching them never requires a
    test-approval record.
    """
    normalized = path.lstrip("./")
    if is_test_path(normalized):
        return False
    if any(normalized.startswith(p) for p in _NON_CODE_PREFIXES):
        return False
    if any(normalized.startswith(p) for p in _PROMPT_PREFIXES):
        return True
    return normalized.endswith(".py")


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def check(
    changed_files: list[str],
    approvals: list[dict],
    first_implementation_commit: str | None,
) -> GateResult:
    """Evaluate the test-approval gate.

    Args:
        changed_files: every path the change touches.
        approvals: committed approval records (dicts with the fields above).
        first_implementation_commit: ISO-8601 time of the earliest non-test code
            change in the change, or None when only tests changed.
    """
    result = GateResult(gate="G1")

    code_changed = [p for p in changed_files if is_code_path(p)]
    # Tests that need a test-approval record. Gate-infrastructure tests
    # (tests/gates/...) are tooling for the gate itself, not application tests,
    # so they are reviewed like code but are not part of "tests approved before
    # implementation" — they are excluded here just as scripts/gates/ is excluded
    # from ``code_changed``.
    test_changed = [
        p for p in changed_files
        if is_test_path(p) and not is_gate_infrastructure_path(p)
    ]

    if not code_changed:
        # No production code change (tests-only, docs-only, data-only): nothing
        # to approve against. Not applicable rather than a pass.
        result.applicable = False
        return result

    if all(is_gate_infrastructure_path(p) for p in code_changed):
        # Only the gate's own scripts/tests changed: infrastructure maintenance,
        # not application behaviour. G1 does not apply.
        result.applicable = False
        return result

    if not approvals:
        result.violations.append(
            Violation("missing approval", f"{len(code_changed)} code file(s) changed without an approval record")
        )
        return result

    if first_implementation_commit is None:
        # Code changed but we were not told when implementation began; the gate
        # cannot prove ordering, so it fails closed rather than guessing.
        result.violations.append(
            Violation("missing implementation time", "cannot verify approval precedes implementation")
        )
        return result

    impl_time = _parse_iso(first_implementation_commit)
    if impl_time is None:
        result.violations.append(
            Violation("unreadable implementation time", repr(first_implementation_commit))
        )
        return result

    # At least one approval must cover the changed tests and predate implementation.
    for approval in approvals:
        approved_at = _parse_iso(approval.get("approved_at", ""))
        if approved_at is None:
            result.violations.append(
                Violation("unreadable approval time", f"change {approval.get('change_id')!r}")
            )
            continue
        covered = set(approval.get("tests") or [])
        uncovered = [t for t in test_changed if t not in covered]
        if uncovered:
            result.violations.append(
                Violation(
                    "approval does not cover changed tests",
                    ", ".join(sorted(uncovered)),
                )
            )
            continue
        if approved_at >= impl_time:
            result.violations.append(
                Violation(
                    "approval after implementation",
                    f"approved {approved_at.isoformat()} >= implementation {impl_time.isoformat()}",
                )
            )
            continue
        # This approval is valid.
        return result

    return result
