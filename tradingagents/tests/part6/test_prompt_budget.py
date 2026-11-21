"""Prompt/tool output budget controls for the optimized profiles."""

import pytest

from tradingagents.agents.context import report_or_absent
from tradingagents.dataflows.config import run_config
from tradingagents.profiles import build_profile, profile_to_runtime_config
from tradingagents.security.tool_node import _truncate_text

pytestmark = pytest.mark.unit


def test_profiles_map_prompt_and_tool_budgets():
    quick = profile_to_runtime_config(build_profile("quick"))
    standard = profile_to_runtime_config(build_profile("standard"))
    deep = profile_to_runtime_config(build_profile("deep"))

    assert quick["max_tool_rounds"] == 1
    assert standard["max_tool_rounds"] == 2
    assert deep["max_tool_rounds"] == 3
    assert quick["max_tool_output_chars"] < standard["max_tool_output_chars"]
    assert standard["max_tool_output_chars"] < deep["max_tool_output_chars"]
    assert quick["max_tokens"] == 1024
    assert standard["max_tokens"] == 2048
    assert deep["max_tokens"] == 3072


def test_tool_output_truncation_keeps_head_and_tail():
    text = "HEAD" + ("x" * 10_000) + "TAIL"

    truncated = _truncate_text(text, 3000)

    assert len(truncated) < len(text)
    assert truncated.startswith("HEAD")
    assert truncated.endswith("TAIL")
    assert "truncated for prompt budget" in truncated


def test_report_prompt_truncation_uses_the_run_budget():
    with run_config({"report_prompt_chars": 20}):
        report = report_or_absent("x" * 100, "market")

    assert len(report) < 100
    assert "report truncated for prompt budget" in report
