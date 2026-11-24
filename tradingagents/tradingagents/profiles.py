"""Named run profiles and strict override handling."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from tradingagents.contracts.profile import ProfileConfig

DEFAULT_PROFILE = "standard"
_COMMON_TTL = {"prices": 900, "news": 3600, "fundamentals": 86400}
_PROFILES = {
    "quick": ProfileConfig(name="quick", analysts=("market",), debate_rounds=1, risk_rounds=1,
        max_tool_rounds=1, quick_model="deepseek-flash", deep_model="deepseek-v4-pro",
        token_budget=80000, timeout_s=300, cache_ttl=_COMMON_TTL,
        max_tool_output_chars=2000, report_prompt_chars=1000, max_output_tokens=1024),
    "standard": ProfileConfig(name="standard", analysts=("market", "news", "fundamentals"),
        debate_rounds=1, risk_rounds=1, max_tool_rounds=2, quick_model="deepseek-flash",
        deep_model="deepseek-v4-pro", token_budget=150000, timeout_s=720, cache_ttl=_COMMON_TTL,
        max_tool_output_chars=3500, report_prompt_chars=2000, max_output_tokens=2048),
    "deep": ProfileConfig(name="deep", analysts=("market", "social", "news", "fundamentals"),
        debate_rounds=2, risk_rounds=2, max_tool_rounds=3, quick_model="deepseek-flash",
        deep_model="deepseek-v4-pro", token_budget=300000, timeout_s=1800, cache_ttl=_COMMON_TTL,
        max_tool_output_chars=5000, report_prompt_chars=3000, max_output_tokens=3072),
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
                  max_tool_output_chars=profile.max_tool_output_chars,
                  report_prompt_chars=profile.report_prompt_chars,
                  max_tokens=profile.max_output_tokens,
                  quick_think_llm=profile.quick_model,
                  deep_think_llm=profile.deep_model,
                  run_profile=profile.name, token_budget=profile.token_budget,
                  timeout_s=profile.timeout_s, cache_ttl=profile.cache_ttl)
    return config


def resolve_run_profile(
    config: dict[str, Any],
    selected_analysts: Iterable[str] | None = None,
) -> tuple[dict[str, Any], tuple[str, ...] | None]:
    """Resolve a named profile at the composition root.

    A named profile supplies the analysts only when the caller did not choose
    them explicitly. The CLI applies the profile config before construction; a
    programmatic ``TradingAgentsGraph(config={"run_profile": "quick"})`` gets the
    same profile defaults here. Explicit analysts remain an intentional override
    and are not replaced.
    """
    name = config.get("run_profile")
    if name in (None, "", "custom"):
        return dict(config), tuple(selected_analysts) if selected_analysts is not None else None

    profile = build_profile(name)
    if selected_analysts is not None:
        chosen = tuple(selected_analysts)
        invalid = sorted(set(chosen) - set(profile.analysts))
        if invalid:
            raise ValueError(
                f"analysts {invalid} are not allowed for profile {profile.name!r}; "
                f"allowed: {list(profile.analysts)}"
            )
        return dict(config), chosen
    return profile_to_runtime_config(profile, config), profile.analysts
