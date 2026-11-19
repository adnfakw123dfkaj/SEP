import check_ai_use_log as g6

LOG = "docs/ai-use-log.yaml"


def test_code_change_with_any_new_entry_passes():
    # A new entry is sufficient; its change_id need not equal the head SHA
    # (which would be circular), nor any particular value.
    result = g6.check(
        ["tradingagents/agents/x.py", LOG],
        [{"change_id": "pr-42", "summary": "x"}],
    )
    assert result.passed


def test_code_change_without_log_blocks():
    result = g6.check(["tradingagents/agents/x.py"], None)
    assert not result.passed
    assert any("not updated" in v.reason for v in result.violations)


def test_prompt_change_without_log_blocks():
    result = g6.check(["prompts/prompt_v1.yaml"], None)
    assert not result.passed


def test_log_touched_but_no_new_entry_blocks():
    # The log file was modified but no entries were added (e.g. an empty touch).
    result = g6.check(["tradingagents/agents/x.py", LOG], [])
    assert not result.passed


def test_docs_only_change_not_applicable():
    result = g6.check(["docs/readme.md"], None)
    assert result.applicable is False
    assert result.status == "skipped"


def test_change_id_is_informational():
    # Any change_id value passes; the gate never blocks on a value/mismatch.
    result = g6.check(
        ["tradingagents/agents/x.py", LOG],
        [{"change_id": "whatever", "summary": "unrelated"}],
    )
    assert result.passed


def test_tests_py_is_not_code_for_gate():
    assert g6.is_code_or_prompt("tests/test_x.py") is False
    assert g6.is_code_or_prompt("tradingagents/tests/req/test_x.py") is False
    assert g6.is_code_or_prompt("tradingagents/tests/security/test_secret_redaction.py") is False
    assert g6.is_code_or_prompt("tradingagents/agents/x.py") is True
    assert g6.is_code_or_prompt("scripts/gates/run.py") is True
    assert g6.is_code_or_prompt("prompts/p.yaml") is True
