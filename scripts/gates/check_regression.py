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

import re

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


def _base_of(test_id: str) -> str:
    """The ``path::function`` part of a node id, dropping any ``[...]`` params."""
    return test_id.split("[", 1)[0]


# pytest falls back to automatic ids like ``text0``/``param1`` for parameters whose
# text has no readable id (special/non-ASCII characters, some versions). Such a
# placeholder carries no mapping to the original text, so the same test gets a
# different node id across environments.
_AUTO_ID = re.compile(r"^(text|param)?\d+$")


def _is_auto_id_suffix(suffix: str) -> bool:
    # suffix is the content inside the last ``[...]`` of a node id
    return bool(_AUTO_ID.match(suffix.strip().rstrip("-")))


def _last_param_suffix(test_id: str) -> str | None:
    if "[" not in test_id or not test_id.endswith("]"):
        return None
    return test_id[test_id.rfind("[") + 1 : -1]


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

    # Group current parameterized ids by their base (path::function) so an
    # auto-generated id (text6) can stand in for a full-text id that pytest named
    # differently. Only same-base, same-count substitution is allowed.
    current_by_base: dict[str, list[tuple[str, str]]] = {}
    for cid, outcome in current.items():
        current_by_base.setdefault(_base_of(cid), []).append((cid, outcome))

    def _resolve(nid: str, test_id: str) -> str | None:
        outcome = current_norm.get(nid)
        if outcome is not None:
            return outcome
        # Fallback: baseline has a full-text param id; current produced an
        # auto id (textN) for the same base with the same number of params.
        suffix = _last_param_suffix(test_id)
        if suffix is None or _is_auto_id_suffix(suffix):
            return None  # not the mismatch case we can safely bridge
        base = _base_of(test_id)
        candidates = current_by_base.get(base, [])
        if not candidates:
            return None
        baseline_count = sum(1 for b in baseline if _base_of(b) == base)
        auto = [
            (cid, o) for cid, o in candidates
            if (s := _last_param_suffix(cid)) is not None and _is_auto_id_suffix(s)
        ]
        # Only bridge when every current id for this base is an auto id and the
        # counts match, so we are not masking a real removal.
        if auto and len(auto) == len(candidates) == baseline_count:
            # Any present outcome is the best evidence; a failure among them
            # should still be reported.
            for _cid, o in auto:
                if o in (FAIL, ERROR):
                    return o
            return PASS
        return None

    for test_id, base_outcome in baseline.items():
        if base_outcome != PASS:
            # Nothing to regress from a test that was already not passing.
            continue
        nid = _norm_id(test_id)
        outcome = _resolve(nid, test_id)
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
