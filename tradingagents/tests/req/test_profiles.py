"""REQ-FR-001 — Quick/Standard/Deep run profiles (Part 1).

Traceable to test-cases/part1-profiles-preflight.md TC-P1-FR001-01..06. The
subject ``tradingagents.profiles`` is not implemented yet; each test skips with a
reason until it is.
"""

from tests.req._support import require

PROFILES = "tradingagents.profiles"


def test_profile_matrix():
    """TC-P1-FR001-01: three profiles match the documented matrix."""
    require(PROFILES)


def test_manifest_profile():
    """TC-P1-FR001-02: manifest records profile and overrides."""
    require(PROFILES)


def test_invalid_override():
    """TC-P1-FR001-03: invalid override is rejected before the run."""
    require(PROFILES)


def test_cli_selects_profile():
    """TC-P1-FR001-04: --profile selects the profile."""
    require(PROFILES)


def test_default_profile_when_unset():
    """TC-P1-FR001-05: default profile applies when unset."""
    require(PROFILES)


def test_env_precedence_over_profile(monkeypatch):
    """TC-P1-FR001-06: env override wins over profile defaults."""
    monkeypatch.setenv("TRADINGAGENTS_MAX_DEBATE_ROUNDS", "5")
    require(PROFILES)
