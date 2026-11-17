"""Gate 2 — Static analysis gate (PDF §6.2).

Lint, type-checking and dependency checks run on every commit; contract,
security, API-surface and permission checks run on any change touching a
safety-relevant path.

This script holds the *policy* half of the gate: which checks must run for a
given set of changed files, and whether the results the workflow collected are
all clean. Running the actual tools (ruff, pyright, pip-audit, ...) is the
workflow's job; it feeds their pass/fail back in as plain data so the decision is
deterministic and testable offline.
"""

from __future__ import annotations

from common import GateResult, Violation

# Paths whose changes escalate the gate to the heavy checks.
SAFETY_RELEVANT_PATHS = (
    "tradingagents/agents/",
    "tradingagents/memory/",
    "tradingagents/dataflows/",
    "tradingagents/security/",
    "tradingagents/contracts/",
    "tradingagents/graph/",
    "scripts/gates/",
)

ALWAYS_ON_CHECKS: tuple[str, ...] = ("lint", "type_check", "dependencies")
SAFETY_ONLY_CHECKS: tuple[str, ...] = ("contract", "security", "api_surface", "permission")


def required_checks(changed_files: list[str]) -> list[str]:
    """The checks that must run for this change.

    Always-on checks run for every change. The heavy checks are added only when
    a changed path is on a safety-relevant tree.
    """
    checks = list(ALWAYS_ON_CHECKS)
    if any(_touches_safety(p) for p in changed_files):
        checks.extend(SAFETY_ONLY_CHECKS)
    return checks



def _touches_safety(path: str) -> bool:
    normalized = path.lstrip("./")
    return any(normalized.startswith(prefix) for prefix in SAFETY_RELEVANT_PATHS)


def check(changed_files: list[str], check_results: dict[str, bool]) -> GateResult:
    """Evaluate the static-analysis gate.

    Args:
        changed_files: every path the change touches.
        check_results: mapping of check name -> True if the check passed. A
            check the policy requires but that is absent from this mapping is
            treated as "not run" and therefore a violation (a required check that
            did not run cannot pass).
    """
    result = GateResult(gate="G2")
    for name in required_checks(changed_files):
        if name not in check_results:
            result.violations.append(Violation(f"required check not run: {name}"))
            continue
        if not check_results[name]:
            result.violations.append(Violation(f"check failed: {name}"))
    return result
