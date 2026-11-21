import pytest

from tradingagents.contracts.profile import ProfileConfig
from tradingagents.contracts.preflight import PreflightResult
from tradingagents.profiles import build_profile


def test_profile_contracts_validate_defaults():
    for name, rounds, tools, tokens, timeout in (
        ("quick", 1, 6, 25000, 300), ("standard", 1, 10, 60000, 720), ("deep", 2, 15, 150000, 1800)
    ):
        p = build_profile(name)
        assert (p.debate_rounds, p.max_tool_rounds, p.token_budget, p.timeout_s) == (rounds, tools, tokens, timeout)
    assert PreflightResult(ticker="AAPL", resolved=True, data_available=True).ok
    assert not PreflightResult(ticker="AAPL", resolved=False, data_available=False).ok


def test_profile_contract_rejects_invalid_values():
    with pytest.raises(ValueError):
        ProfileConfig(name="bad", analysts=(), debate_rounds=0, risk_rounds=1, max_tool_rounds=1,
                      quick_model="q", deep_model="d", token_budget=1, timeout_s=1, cache_ttl={})
