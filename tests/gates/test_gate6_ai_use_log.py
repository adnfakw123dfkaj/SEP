import check_ai_use_log as g6

LOG = "docs/ai-use-log.yaml"


def test_code_change_with_log_entry_passes():
    result = g6.check(
        ["tradingagents/agents/x.py", LOG],
        [{"change_id": "chg-1", "summary": "x"}],
        "chg-1",
    )
    assert result.passed


def test_code_change_without_log_blocks():
    result = g6.check(["tradingagents/agents/x.py"], None, "chg-1")
    assert not result.passed
    assert any("not updated" in v.reason for v in result.violations)


def test_prompt_change_without_log_blocks():
    result = g6.check(["prompts/prompt_v1.yaml"], None, "chg-1")
    assert not result.passed


def test_docs_only_change_not_applicable():
    result = g6.check(["docs/readme.md"], None, "chg-1")
    assert result.applicable is False
    assert result.status == "skipped"


def test_log_entry_missing_change_id_blocks():
    result = g6.check(
        ["tradingagents/agents/x.py", LOG],
        [{"change_id": "other", "summary": "unrelated"}],
        "chg-1",
    )
    assert not result.passed
    assert any("missing change id" in v.reason for v in result.violations)


def test_tests_py_is_not_code_for_gate():
    assert g6.is_code_or_prompt("tests/test_x.py") is False
    assert g6.is_code_or_prompt("tradingagents/agents/x.py") is True
    assert g6.is_code_or_prompt("prompts/p.yaml") is True
