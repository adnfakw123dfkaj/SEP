"""Shared result model for the blocking-gate checks.

Every gate check is a pure function that takes plain inputs and returns a
``GateResult``. The result says whether the gate passes, the machine reason, and
any human-readable violations. The CLI wrapper turns a failed result into a
non-zero exit code; the pytest suite (``tests/gates``) calls the same functions
directly with synthetic inputs.

Nothing here reaches the network or GitHub. The workflow layer is responsible for
supplying the inputs (changed files, commit times, PR metadata) as plain data.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Violation:
    """One rule violation a gate found."""

    reason: str
    detail: str = ""


@dataclass
class GateResult:
    """The outcome of one gate check.

    ``gate`` is the gate id (``G1``..``G6``). ``blocking`` is False for a
    warning-only (layer-1) run: the violations are still reported, but the caller
    must not fail the build on them. ``applicable`` is False when the gate does
    not apply to this change (e.g. a docs-only PR for the semantic-eval gate);
    that is recorded as skipped, not passed or failed.
    """

    gate: str
    violations: list[Violation] = field(default_factory=list)
    applicable: bool = True

    @property
    def passed(self) -> bool:
        return not self.violations

    @property
    def status(self) -> str:
        if not self.applicable:
            return "skipped"
        return "pass" if self.passed else "fail"

    def to_dict(self) -> dict:
        return {
            "gate": self.gate,
            "status": self.status,
            "violations": [{"reason": v.reason, "detail": v.detail} for v in self.violations],
        }

    def render(self) -> str:
        """A one-block human summary for CI logs."""
        lines = [f"gate {self.gate}: {self.status}"]
        for v in self.violations:
            line = f"  - {v.reason}"
            if v.detail:
                line += f": {v.detail}"
            lines.append(line)
        return "\n".join(lines)


def exit_code(result: GateResult, warn_only: bool = False) -> int:
    """The process exit code a CLI wrapper should return for ``result``.

    A warning-only run (layer 1, branch self-check) never fails the build: it
    reports violations but exits 0. A blocking run (layer 2, PR to master) fails.
    A skipped gate passes.
    """
    if not result.applicable or result.passed or warn_only:
        return 0
    return 1
