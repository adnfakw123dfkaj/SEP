from unittest.mock import Mock

import pytest

from tradingagents.preflight import validate_request


def test_invalid_ticker_does_not_call_provider(monkeypatch):
    ticker = Mock()
    monkeypatch.setattr("tradingagents.dataflows.router.route_to_vendor", ticker)
    result = validate_request("bad ticker!")
    assert not result.ok and not result.resolved
    ticker.assert_not_called()


def test_no_data_is_distinct_from_invalid(monkeypatch):
    ticker = Mock(return_value="No data available for AAPL")
    monkeypatch.setattr("tradingagents.dataflows.router.route_to_vendor", ticker)
    result = validate_request("AAPL", "2026-11-20")
    assert result.resolved and not result.data_available
    assert "no price history" in result.reason


def test_valid_tickers_use_normalized_symbol(monkeypatch):
    seen = []

    def fake_route(tool, symbol, *args):
        seen.append(symbol)
        return "Date Open High Low Close Volume\n2026-11-20 1 1 1 1 1"
    monkeypatch.setattr("tradingagents.dataflows.router.route_to_vendor", fake_route)
    for symbol in ("AAPL", "0700.HK", "BTC-USD"):
        assert validate_request(symbol, "2026-11-20").ok
    assert seen == ["AAPL", "0700.HK", "BTC-USD"]


@pytest.mark.parametrize("symbol", ["AAPL", "0700.HK", "BTC-USD", "^GSPC"])
def test_valid_tickers(monkeypatch, symbol):
    monkeypatch.setattr("tradingagents.dataflows.router.route_to_vendor", lambda *a: "Close: 1.00")
    assert validate_request(symbol, "2026-11-20").ok


def test_no_analyst_calls(monkeypatch):
    """A failed preflight exits before graph construction / analyst execution."""
    import cli.run as run
    from cli.models import AnalystType

    monkeypatch.setattr(run, "get_user_selections", lambda flags=None: {
        "ticker": "AAPL", "analysis_date": "2026-11-20", "asset_type": "stock",
        "analysts": [AnalystType.MARKET], "research_depth": 1,
        "quick_think_llm": "test", "deep_think_llm": "test", "backend_url": None,
        "llm_provider": "openai", "output_language": "English",
    })
    from tradingagents.contracts.preflight import PreflightResult

    monkeypatch.setattr(run, "validate_request", lambda *a: PreflightResult(
        ticker="AAPL", resolved=True, data_available=False, reason="no data"
    ))
    graph = Mock()
    monkeypatch.setattr(run, "TradingAgentsGraph", graph)
    with pytest.raises(run.typer.Exit):
        run.run_analysis(flags={"profile": "quick", "ticker": "AAPL", "date": "2026-11-20",
                                "analysts": "market", "save": False, "show": False})
    graph.assert_not_called()
