"""Gate 6 — AI-use log gate (PDF §6.6).

A pull request that changes code or prompts without updating the AI-use log is
blocked.

Rule: if the change touches production code (a ``.py`` file outside tests, docs
and ``.github``) or a prompt, then ``docs/ai-use-log.yaml`` must also change in
the same change, and the new log entries must reference this change's id.
"""

from __future__ import annotations

from common import GateResult, Violation

AI_USE_LOG_PATH = "docs/ai-use-log.yaml"
PROMPT_MODEL_PATHS = ("prompts/",)
PROMPT_MODEL_SUFFIXES = ("_analyst.py", "prompts.py")
# Trees whose .py files are not "production code" for this gate.
_NON_CODE_PREFIXES = ("tests/", "docs/", ".github/", "test-cases/", "scripts/gates/tests/")


def is_code_or_prompt(path: str) -> bool:
    """Whether changing ``path`` requires an AI-use-log update."""
    normalized = path.lstrip("./")
    if any(normalized.startswith(p) for p in PROMPT_MODEL_PATHS):
        return True
    if normalized.endswith(PROMPT_MODEL_SUFFIXES):
        return True
    if not normalized.endswith(".py"):
        return False
    return not any(normalized.startswith(p) for p in _NON_CODE_PREFIXES)


def check(
    changed_files: list[str],
    new_log_entries: list[dict] | None,
    change_id: str | None,
) -> GateResult:
    """Evaluate the AI-use-log gate.

    Args:
        changed_files: every path the change touches.
        new_log_entries: the entries added to the AI-use log in this change (None
            when the log was not touched).
        change_id: this change's identifier; entries must reference it.
    """
    result = GateResult(gate="G6")

    needs_log = any(is_code_or_prompt(p) for p in changed_files)
    if not needs_log:
        result.applicable = False
        return result

    log_touched = AI_USE_LOG_PATH in {p.lstrip("./") for p in changed_files}
    if not log_touched or not new_log_entries:
        result.violations.append(
            Violation("AI-use log not updated", "code/prompt changed without a new log entry")
        )
        return result

    if change_id:
        referencing = [e for e in new_log_entries if e.get("change_id") == change_id]
        if not referencing:
            result.violations.append(
                Violation("log entry missing change id", f"no entry references {change_id!r}")
            )
    return result
