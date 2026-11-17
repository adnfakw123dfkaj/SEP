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

# pytest may or may not escape special characters inside a parameterized test id
# depending on its version (e.g. ``\\n`` vs a real newline). ``_norm_id`` collapses
# both forms to the same token so a baseline recorded under one pytest version
# matches a run under another.


def _norm_id(test_id: str) -> str:
    """Canonicalise a pytest node id so parameter escaping differences do not
    make an identical test look missing (pytest changes id escaping between
    versions). The base (path::function) and the set of parameters are
    preserved; only how special characters are written is normalised.
    """
    # Normalise escape sequences from both "escaped" and "raw" forms to tokens.
    out = []
    i = 0
    while i < len(test_id):
        ch = test_id[i]
        if ch == "\\" and i + 1 < len(test_id):
            nxt = test_id[i + 1]
            out.append({"n": "\x00N", "r": "\x00R", "t": "\x00T"}.get(nxt, "\x00B"))
            i += 2
            continue
        if ch == "\n":
            out.append("\x00N")
        elif ch == "\r":
            out.append("\x00R")
        elif ch == "\t":
            out.append("\x00T")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


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

    # Index current outcomes and approved deletions by a normalised id so
    # parameter-escaping differences between pytest versions do not register as
    # deletions. Keep the original id for reporting.
    current_norm: dict[str, str] = {}
    for cid, outcome in current.items():
        current_norm.setdefault(_norm_id(cid), outcome)
    approved_norm = {_norm_id(d) for d in approved_deletes}

    for test_id, base_outcome in baseline.items():
        if base_outcome != PASS:
            # Nothing to regress from a test that was already not passing.
            continue
        nid = _norm_id(test_id)
        outcome = current_norm.get(nid)
        if outcome is None:
            # A previously-passing test vanished. Allowed only with an approval
            # that explicitly authorises deleting it; otherwise it blocks.
            if nid not in approved_norm:
                result.violations.append(
                    Violation("previously-passing test deleted without approval", test_id)
                )
            continue
        if outcome in (FAIL, ERROR):
            result.violations.append(
                Violation(f"regression: {outcome}", test_id)
            )

    return result
