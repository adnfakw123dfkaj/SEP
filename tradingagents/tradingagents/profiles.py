"""Named run profiles and strict override handling."""
from __future__ import annotations

from tradingagents.contracts.profile import ProfileConfig

_COMMON_TTL = {"prices": 900, "news": 3600, "fundamentals": 86400}
_PROFILES = {
    "quick": ProfileConfig(name="quick", analysts=("market",), debate_rounds=1, risk_rounds=1,
        max_tool_rounds=6, quick_model="deepseek-flash", deep_model="deepseek-v4-pro",
        token_budget=25000, timeout_s=300, cache_ttl=_COMMON_TTL),
    "standard": ProfileConfig(name="standard", analysts=("market", "news", "fundamentals"),
        debate_rounds=1, risk_rounds=1, max_tool_rounds=10, quick_model="deepseek-flash",
        deep_model="deepseek-v4-pro", token_budget=60000, timeout_s=720, cache_ttl=_COMMON_TTL),
    "deep": ProfileConfig(name="deep", analysts=("market", "social", "news", "fundamentals"),
        debate_rounds=2, risk_rounds=2, max_tool_rounds=15, quick_model="deepseek-flash",
        deep_model="deepseek-v4-pro", token_budget=150000, timeout_s=1800, cache_ttl=_COMMON_TTL),
}


def build_profile(name: str, overrides: dict | None = None) -> ProfileConfig:
    """Return a validated profile; unknown names/fields fail clearly."""
    key = str(name).strip().lower()
    if key not in _PROFILES:
        raise ValueError(f"unknown profile {name!r}; choose quick, standard, or deep")
    values = _PROFILES[key].model_dump()
    overrides = overrides or {}
    unknown = set(overrides) - set(values)
    if unknown:
        raise ValueError(f"unknown {key} profile override fields: {', '.join(sorted(unknown))}")
    values.update(overrides)
    try:
        return ProfileConfig.model_validate(values)
    except Exception as exc:
        raise ValueError(f"invalid {key} profile override: {exc}") from exc


def profile_to_runtime_config(profile: ProfileConfig, base: dict | None = None) -> dict:
    """Map the public profile contract onto existing TradingAgents config keys."""
    config = dict(base or {})
    config.update(max_debate_rounds=profile.debate_rounds,
                  max_risk_discuss_rounds=profile.risk_rounds,
                  max_tool_rounds=profile.max_tool_rounds,
                  quick_think_llm=profile.quick_model,
                  deep_think_llm=profile.deep_model,
                  run_profile=profile.name, token_budget=profile.token_budget,
                  timeout_s=profile.timeout_s, cache_ttl=profile.cache_ttl)
    return config
