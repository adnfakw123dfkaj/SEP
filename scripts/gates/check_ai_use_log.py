"""Gate 6 — AI-use log gate (PDF §6.6).

A pull request that changes code or prompts without updating the AI-use log is
blocked.

Rule: if the change touches production code (a ``.py`` file outside tests, docs
and ``.github``) or a prompt, then ``docs/ai-use-log.yaml`` must also change in
the same change, adding **at least one new entry**.

The gate deliberately does **not** require the entry's ``change_id`` to equal the
commit's head SHA: a commit that adds the log entry changes the head SHA itself,
so a SHA requirement is circular and can never be satisfied. A new entry is the
evidence; its ``change_id`` is informational (a stable id such as a PR number,
branch name, or a hand-written id is fine).
"""

from __future__ import annotations

from common import GateResult, Violation

AI_USE_LOG_PATH = "docs/ai-use-log.yaml"
PROMPT_MODEL_PATHS = ("prompts/",)
PROMPT_MODEL_SUFFIXES = ("_analyst.py", "prompts.py")
# Directory segments / prefixes whose .py files are not "production code" for
# this gate. Tests live under a ``tests/`` segment at any depth (e.g.
# ``tests/req/...`` and ``tradingagents/tests/req/...``), plus docs, CI config
# and the test-case specs.
_NON_CODE_PREFIXES = ("docs/", ".github/", "test-cases/")
_TEST_SUFFIXES = ("_test.py",)
_TEST_DIR_SEGMENT = "tests/"


def _is_test_file(normalized: str) -> bool:
    """True for any file inside a ``tests/`` directory or named ``test_*/…_test``."""
    segments = normalized.split("/")
    if _TEST_DIR_SEGMENT.rstrip("/") in segments[:-1]:
        return True
    name = segments[-1] if segments else ""
    return name.startswith("test_") or normalized.endswith(_TEST_SUFFIXES)


def is_code_or_prompt(path: str) -> bool:
    """Whether changing ``path`` requires an AI-use-log update."""
    normalized = path.lstrip("./")
    if any(normalized.startswith(p) for p in PROMPT_MODEL_PATHS):
        return True
    if normalized.endswith(PROMPT_MODEL_SUFFIXES):
        return True
    if not normalized.endswith(".py"):
        return False
    if _is_test_file(normalized):
        return False
    return not any(normalized.startswith(p) for p in _NON_CODE_PREFIXES)


def check(
    changed_files: list[str],
    new_log_entries: list[dict] | None,
    change_id: str | None = None,
) -> GateResult:
    """Evaluate the AI-use-log gate.

    Args:
        changed_files: every path the change touches.
        new_log_entries: the entries added to the AI-use log in this change (None
            when the log was not touched).
        change_id: unused for blocking. Kept for callers that pass a stable id;
            the gate does not require entries to match it (see module docstring).
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

    return result
