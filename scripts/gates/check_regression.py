"""Gate 5 — Regression gate (PDF §6.5).

Every change runs the full prior test suites (plus the change's own tests); any
regression blocks the merge.

A *regression* is a test that was passing on ``master`` and now fails or errors
(including collection errors — an import failure is a regression, not a skip).

Tests may be **modified or deleted** by a branch, but a deletion must be
**approved**: when a previously-passing test is now missing, the change must carry
a deletion approval (an entry in ``docs/approvals`` naming that test) or the gate
blocks. This keeps "delete a test" allowed but auditable, and prevents deleting
tests to make a red change pass.
"""

from __future__ import annotations

from common import GateResult, Violation

PASS = "passed"
FAIL = "failed"
ERROR = "error"
SKIP = "skipped"


def _approved_deletions(approvals: list[dict] | None) -> set[str]:
    """Test ids an approval record explicitly authorises to delete."""
    approved: set[str] = set()
    for record in approvals or []:
        approved.update(record.get("deletes") or [])
    return approved


def check(
    baseline: dict[str, str],
    current: dict[str, str],
    approvals: list[dict] | None = None,
) -> GateResult:
    """Evaluate the regression gate.

    Args:
        baseline: test id -> outcome on ``master`` (the prior green state).
        current: test id -> outcome after the change.
        approvals: committed approval records; those with a ``deletes`` list
            authorise removing the named tests. A missing test not covered here
            blocks.
    """
    result = GateResult(gate="G5")
    approved_deletes = _approved_deletions(approvals)

    for test_id, base_outcome in baseline.items():
        if base_outcome != PASS:
            # Nothing to regress from a test that was already not passing.
            continue
        outcome = current.get(test_id)
        if outcome is None:
            # A previously-passing test vanished. Allowed only with an approval
            # that explicitly authorises deleting it; otherwise it blocks.
            if test_id not in approved_deletes:
                result.violations.append(
                    Violation("previously-passing test deleted without approval", test_id)
                )
            continue
        if outcome in (FAIL, ERROR):
            result.violations.append(
                Violation(f"regression: {outcome}", test_id)
            )

    return result
