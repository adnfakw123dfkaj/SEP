"""Per-profile token budgets for Part 6 routing.

Hard limits come from the acceptance targets in the requirements document.
Soft limits are the target (not the cap), so crossing the target triggers
summarisation before the run reaches the hard stop.
"""

from __future__ import annotations

from typing import Any

from tradingagents.contracts.cost import Budget

_PROFILE_LIMITS: dict[str, tuple[int, int]] = {
    # profile: (soft target, hard acceptance cap)
    "quick": (20_000, 25_000),
    "standard": (50_000, 60_000),
    "deep": (120_000, 150_000),
}


def budget_for_profile(
    profile: str,
    *,
    profile_config: Any | None = None,
) -> Budget:
    """Build the budget for ``profile``.

    ``profile_config`` (Part 1) is the source of truth when it carries
    ``soft_token_limit`` / ``hard_token_limit``.  Otherwise the documented
    presets apply, so Part 6 can run with a stub while Part 1 is in progress.
    """
    if profile_config is not None:
        name = getattr(profile_config, "name", None) or profile
        preset = _PROFILE_LIMITS.get(profile) or _PROFILE_LIMITS.get(name)
        soft = getattr(profile_config, "soft_token_limit", None)
        hard = getattr(profile_config, "hard_token_limit", None)
        if soft is None and preset is not None:
            soft = preset[0]
        if hard is None and preset is not None:
            hard = preset[1]
        if soft is not None and hard is not None:
            return Budget(
                profile=name,
                soft_limit=int(soft),
                hard_limit=int(hard),
                currency="CNY",
            )

    if profile not in _PROFILE_LIMITS:
        raise ValueError(
            f"Unknown run profile {profile!r}; expected one of "
            f"{', '.join(sorted(_PROFILE_LIMITS))}"
        )

    soft, hard = _PROFILE_LIMITS[profile]
    return Budget(profile=profile, soft_limit=soft, hard_limit=hard, currency="CNY")
