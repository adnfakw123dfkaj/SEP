"""Offline integration checks for the named profile CLI path."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import cli.main as cli_main
import cli.run as cli_run


@pytest.mark.parametrize(
    ("profile", "analysts", "debate", "risk", "tool_rounds", "budget", "timeout"),
    [
        ("quick", ("market",), 1, 1, 1, 80_000, 300),
        ("standard", ("market", "news", "fundamentals"), 1, 1, 2, 150_000, 720),
        ("deep", ("market", "social", "news", "fundamentals"), 2, 2, 3, 300_000, 1800),
    ],
)
def test_profile_option_reaches_cli_and_builds_runtime_config(
    profile, analysts, debate, risk, tool_rounds, budget, timeout, monkeypatch
):
    """The CLI option is forwarded and controls the effective run settings."""
    captured = {}
    monkeypatch.setattr(cli_main, "run_analysis", lambda **kwargs: captured.update(kwargs))

    result = CliRunner().invoke(cli_main.app, ["--profile", profile])
    assert result.exit_code == 0, result.output
    assert captured["flags"]["profile"] == profile

    selections = {
        "profile": profile,
        "research_depth": 5,  # Would incorrectly override the profile if precedence regressed.
        "quick_think_llm": "deepseek-flash",
        "deep_think_llm": "deepseek-v4-pro",
        "backend_url": None,
        "llm_provider": "deepseek",
        "output_language": "English",
    }
    with patch.object(cli_run, "DEFAULT_CONFIG", dict(cli_run.DEFAULT_CONFIG)):
        config = cli_run._build_run_config(selections, checkpoint=None)

    assert config["run_profile"] == profile
    assert config["max_debate_rounds"] == debate
    assert config["max_risk_discuss_rounds"] == risk
    assert config["max_tool_rounds"] == tool_rounds
    assert config["token_budget"] == budget
    assert config["timeout_s"] == timeout
    assert analysts  # Analyst defaults are separately applied in run_analysis.


def test_explicit_analysts_override_quick_defaults(monkeypatch):
    """An explicit --analysts selection is retained alongside a profile."""
    captured = {}
    monkeypatch.setattr(cli_main, "run_analysis", lambda **kwargs: captured.update(kwargs))
    result = CliRunner().invoke(
        cli_main.app,
        ["--profile", "quick", "--analysts", "market,news"],
    )
    assert result.exit_code == 0, result.output
    assert captured["flags"]["profile"] == "quick"
    assert captured["flags"]["analysts"] == "market,news"


def test_standard_and_deep_enable_checkpoint_by_default(monkeypatch):
    monkeypatch.delenv("TRADINGAGENTS_CHECKPOINT_ENABLED", raising=False)
    base = {
        "research_depth": 1,
        "quick_think_llm": "q",
        "deep_think_llm": "d",
        "backend_url": None,
        "llm_provider": "openai",
        "output_language": "English",
    }
    standard = cli_run._build_run_config({**base, "profile": "standard"}, None)
    deep = cli_run._build_run_config({**base, "profile": "deep"}, None)
    quick = cli_run._build_run_config({**base, "profile": "quick"}, None)

    assert standard["checkpoint_enabled"] is True
    assert deep["checkpoint_enabled"] is True
    assert quick["checkpoint_enabled"] is False


def test_headless_run_defaults_to_standard_profile(monkeypatch):
    """With no profile, no analysts and no terminal, Standard is the default."""
    from cli.models import AnalystType
    from tradingagents.contracts.preflight import PreflightResult

    captured = {}
    monkeypatch.setattr(
        cli_run.sys,
        "stdin",
        type("S", (), {"isatty": lambda self: False})(),
    )
    monkeypatch.setattr(cli_run, "unattended_gaps", lambda flags: [])
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags: captured.update(flags) or {
        "ticker": "AAPL", "analysis_date": "2026-11-20", "asset_type": "stock",
        "analysts": [AnalystType.MARKET], "research_depth": 1,
        "quick_think_llm": "q", "deep_think_llm": "d", "backend_url": None,
        "llm_provider": "openai", "output_language": "English",
    })
    monkeypatch.setattr(
        cli_run,
        "validate_request",
        lambda *a, **k: PreflightResult(
            ticker="AAPL", resolved=True, data_available=False, reason="stop"
        ),
    )

    with pytest.raises(cli_run.typer.Exit):
        cli_run.run_analysis(flags={
            "ticker": "AAPL", "date": "2026-11-20", "save": False, "show": False,
        })

    assert captured["profile"] == "standard"
