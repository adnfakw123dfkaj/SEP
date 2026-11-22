"""Live end-to-end integration for the new requirements.

These run the real pipeline against a configured provider and assert the
artifacts the requirements demand from an actual run — the evidence chain, the
run manifest, the cost report, a deterministic rating, and point-in-time
integrity. They are ``integration`` tests (excluded from the offline/CI suite) and
skip when no provider API key is configured.

Covers (live evidence):
  REQ-FR-004  evidence refs + manifest produced by a run
  REQ-QUAL-002 report fidelity over the produced report
  REQ-COST-001 token/cost report present, no silent over-budget
  REQ-INV-003 committed rating in the closed set (or REVIEW)
  REQ-INV-002 no future-dated data (historical run)

Run:
    cd tradingagents
    python -m pytest tests/req/test_live_end_to_end.py -m integration -q
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from tradingagents.agents.rating import RATING_REVIEW, RATINGS_5_TIER
from tradingagents.default_config import DEFAULT_CONFIG

pytestmark = pytest.mark.integration

_ALLOWED_RATINGS = set(RATINGS_5_TIER) | {RATING_REVIEW}


# provider -> (api-key env, default quick/deep model)
_PROVIDERS = {
    # models must exist in the cost price table (see cost/pricing.py)
    "deepseek": ("DEEPSEEK_API_KEY", "deepseek-flash", "deepseek-v4-pro"),
    "openai": ("OPENAI_API_KEY", "gpt-6-luna", "gpt-6-sol"),
    "anthropic": ("ANTHROPIC_API_KEY", "claude-haiku-4-5", "claude-opus-5-5"),
    "google": ("GOOGLE_API_KEY", "gemini-3.8-flash", "gemini-3.8-max"),
    "xai": ("XAI_API_KEY", "grok-4-fast", "grok-4"),
    "openrouter": ("OPENROUTER_API_KEY", "openai/gpt-6-luna", "openai/gpt-6-sol"),
}


def _project_env_values() -> dict:
    """Read the project's ``.env`` directly (cwd-independent).

    The offline ``tests/conftest.py`` blanks ``TRADINGAGENTS_*`` and substitutes
    ``placeholder`` for absent keys before the package imports, so we cannot rely
    on the process environment alone to tell whether a real provider key exists.
    We parse the ``.env`` beside the project (``tradingagents/.env``) ourselves.
    """
    try:
        from dotenv import dotenv_values
    except Exception:
        return {}
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        candidate = os.path.join(d, ".env")
        if os.path.isfile(candidate):
            return {k: v for k, v in dotenv_values(candidate).items() if v}
        d = os.path.dirname(d)
    return {}


def _real_key(env_name: str) -> bool:
    """A real key is present (env or project .env), not empty or the placeholder."""
    value = os.environ.get(env_name) or ""
    if not value or value == "placeholder":
        value = _project_env_values().get(env_name, "")
    return bool(value) and value != "placeholder"


def _pick_provider():
    """Choose (provider, key_env, quick, deep) for a live run.

    The offline ``conftest`` blanks ``TRADINGAGENTS_LLM_PROVIDER`` and substitutes
    ``placeholder`` for missing keys, so we do not trust the provider overlay: we
    look for a genuinely-configured provider key among the known providers.
    ``.env`` is loaded by importing ``tradingagents`` (done at module import), so
    the real key is in the environment.
    """
    env_values = _project_env_values()
    configured = (
        os.environ.get("TRADINGAGENTS_LLM_PROVIDER")
        or env_values.get("TRADINGAGENTS_LLM_PROVIDER", "")
    ).strip().lower()
    if configured in _PROVIDERS and _real_key(_PROVIDERS[configured][0]):
        return configured, *_PROVIDERS[configured]
    for provider, (env_name, quick, deep) in _PROVIDERS.items():
        if _real_key(env_name):
            return provider, env_name, quick, deep
    return None


_PROVIDER = _pick_provider()


needs_key = pytest.mark.skipif(
    _PROVIDER is None,
    reason="no provider API key configured for a live run",
)


@pytest.fixture(scope="module")
def live_run():
    """One real (small, quick-profile) analysis shared by the assertions below."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    provider, _key_env, quick, deep = _PROVIDER
    cfg = DEFAULT_CONFIG.copy()
    tmp = tempfile.mkdtemp(prefix="ta-live-")
    cfg["results_dir"] = os.path.join(tmp, "logs")
    cfg["data_cache_dir"] = os.path.join(tmp, "cache")
    cfg["memory_log_path"] = os.path.join(tmp, "memory.md")
    cfg["llm_provider"] = provider
    cfg["quick_think_llm"] = quick
    cfg["deep_think_llm"] = deep
    cfg["backend_url"] = None
    # "custom" makes the budget fall back to effectively-unlimited, so a real
    # run completes and produces its evidence/manifest (the tight per-profile
    # budget and its hard-stop are covered separately in the offline tests).
    cfg["run_profile"] = "custom"
    cfg["max_debate_rounds"] = 1
    cfg["max_risk_discuss_rounds"] = 1

    graph = TradingAgentsGraph(selected_analysts=("market",), config=cfg)
    state, signal = graph.propagate("AAPL", "2026-11-18")
    return graph, state, signal, cfg


@needs_key
def test_manifest_and_evidence_produced(live_run):
    """REQ-FR-004: a real run yields evidence refs and a manifest on disk."""
    _graph, state, _signal, cfg = live_run
    assert "evidence_refs" in state
    assert isinstance(state["evidence_refs"], list)
    # A manifest is written under results_dir/<ticker>/.../manifests
    import pathlib

    manifests = list(pathlib.Path(cfg["results_dir"]).rglob("manifests/*.json"))
    assert manifests, "a run must write a manifest.json (REQ-FR-004)"
    data = json.loads(manifests[0].read_text(encoding="utf-8"))
    for key in ("run_id", "ticker", "date", "rating", "status", "token_usage_by_agent"):
        assert key in data


@needs_key
def test_cost_report_present_no_silent_over_budget(live_run):
    """REQ-COST-001: the run carries a cost report; over-budget is explicit."""
    _graph, state, _signal, _cfg = live_run
    assert "cost_report" in state and state["cost_report"] is not None
    # If the run tripped the budget it must be flagged, never silent.
    if state.get("budget_exceeded"):
        assert state.get("final_rating") == "REVIEW"


@needs_key
def test_rating_in_closed_set(live_run):
    """REQ-INV-003: the committed rating is in the closed set or REVIEW."""
    _graph, _state, signal, _cfg = live_run
    assert signal in _ALLOWED_RATINGS


@needs_key
def test_report_fidelity_of_live_report(live_run):
    """REQ-QUAL-002: the produced report passes structural + citation checks."""
    from tradingagents.evidence.fidelity import (
        citation_support_rate,
        report_schema_valid,
    )

    _graph, state, _signal, _cfg = live_run
    report = state.get("final_trade_decision", "") or ""
    assert report, "a run must produce a final decision"
    # Structural check; a REVIEW run has no tradeable call to validate.
    if state.get("final_rating") != "REVIEW":
        assert report_schema_valid(report), "report must carry Rating + Thesis"
        # Every cited evidence id must resolve in this run's registry.
        cited = state.get("evidence_refs") or []
        known = {ref["id"] for ref in state.get("evidence", []) if "id" in ref}
        if cited:
            assert citation_support_rate(cited, known) >= 0.95


@needs_key
def test_point_in_time_no_future_dates(live_run):
    """REQ-INV-002: a historical run carries no data dated after its trade_date."""
    _graph, state, _signal, _cfg = live_run
    trade_date = state.get("trade_date")
    assert trade_date == "2026-11-18"
    # The verified snapshot, when present, must not cite rows after the run date.
    snapshot = state.get("verified_snapshot", "") or ""
    for line in snapshot.splitlines():
        # rows look like "| 2026-11-17 | 190.2 |"; any date > trade_date would leak
        import re

        m = re.match(r"\|\s*(\d{4}-\d{2}-\d{2})\s*\|", line)
        if m:
            assert m.group(1) <= trade_date, f"future row leaked: {m.group(1)}"
