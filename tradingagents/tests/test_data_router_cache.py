"""Cache integration checks for the shared data vendor router."""
from tradingagents.dataflows import router
from tradingagents.dataflows.config import run_config


def test_route_caches_successful_response(tmp_path, monkeypatch):
    calls = 0

    def vendor(*args, **kwargs):
        nonlocal calls
        calls += 1
        return "fixture-price"

    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance", vendor)
    config = {"data_cache_dir": str(tmp_path),
              "tool_vendors": {"get_stock_data": "yfinance"}}
    with run_config(config):
        assert router.route_to_vendor("get_stock_data", "AAPL", "2026-01-02") == "fixture-price"
        assert router.route_to_vendor("get_stock_data", "AAPL", "2026-01-02") == "fixture-price"
        assert calls == 1


def test_route_cache_key_includes_date(tmp_path, monkeypatch):
    calls = 0

    def vendor(*args, **kwargs):
        nonlocal calls
        calls += 1
        return f"fixture-{args[1]}"

    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance", vendor)
    config = {"data_cache_dir": str(tmp_path),
              "tool_vendors": {"get_stock_data": "yfinance"}}
    with run_config(config):
        router.route_to_vendor("get_stock_data", "AAPL", "2026-01-02")
        router.route_to_vendor("get_stock_data", "AAPL", "2026-01-03")
    assert calls == 2


def test_fresh_cache_prevents_a_vendor_call(tmp_path, monkeypatch):
    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance",
                        lambda *args, **kwargs: "fixture-price")
    config = {"data_cache_dir": str(tmp_path),
              "tool_vendors": {"get_stock_data": "yfinance"}}
    with run_config(config):
        assert router.route_to_vendor("get_stock_data", "AAPL", "2026-01-02") == "fixture-price"
        calls = []
        monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance",
                            lambda *args, **kwargs: calls.append("called"))
        assert router.route_to_vendor("get_stock_data", "AAPL", "2026-01-02") == "fixture-price"
        assert calls == []


def test_unavailable_sentinel_is_not_cached(tmp_path, monkeypatch):
    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance",
                        lambda *args, **kwargs: "DATA_UNAVAILABLE: timeout")
    config = {"data_cache_dir": str(tmp_path),
              "tool_vendors": {"get_stock_data": "yfinance"}}
    with run_config(config):
        router.route_to_vendor("get_stock_data", "AAPL", "2026-01-02")
        cache_files = list(tmp_path.glob("*.json"))
    assert cache_files == []
