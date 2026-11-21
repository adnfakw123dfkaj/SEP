import pytest

from tradingagents.profiles import build_profile, profile_to_runtime_config


def test_profile_matrix():
    quick, standard, deep = (build_profile(n) for n in ("quick", "standard", "deep"))
    assert quick.analysts == ("market",)
    assert standard.analysts == ("market", "news", "fundamentals")
    assert deep.analysts == ("market", "social", "news", "fundamentals")
    assert [p.max_tool_rounds for p in (quick, standard, deep)] == [6, 10, 15]
    assert [p.token_budget for p in (quick, standard, deep)] == [25000, 60000, 150000]


def test_manifest_profile():
    from tradingagents.contracts.manifest import RunManifest
    config = profile_to_runtime_config(build_profile("quick"))
    manifest = RunManifest(run_id="run-1", ticker="AAPL", date="2026-11-20", profile=config["run_profile"])
    assert manifest.profile == "quick"


def test_invalid_override():
    with pytest.raises(ValueError, match="unknown profile"):
        build_profile("fast")
    with pytest.raises(ValueError, match="invalid quick profile"):
        build_profile("quick", {"token_budget": 0})
    with pytest.raises(ValueError, match="unknown.*fields"):
        build_profile("quick", {"typo": 1})


def test_profile_maps_to_existing_runtime_config():
    config = profile_to_runtime_config(build_profile("deep"), {"output_language": "Chinese"})
    assert config["max_debate_rounds"] == config["max_risk_discuss_rounds"] == 2
    assert config["max_tool_rounds"] == 15 and config["output_language"] == "Chinese"
