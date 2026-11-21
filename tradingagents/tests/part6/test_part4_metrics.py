"""Part 4 vendor, PIT, cache, resume and fallback metrics."""

import importlib.metadata

import pytest

from tradingagents.cache import CacheController
from tradingagents.cache.metrics import CacheMetrics, cache_metrics_scope
from tradingagents.contracts.cache import CacheKey
from tradingagents.dataflows.pit import PIT_COVERAGE, pit_coverage
from tradingagents.dataflows.vendor_versions import vendor_versions
from tradingagents.resilience import FailureEvent, summarize_fallback_events

pytestmark = pytest.mark.unit


def test_vendor_versions_use_installed_distribution_versions():
    versions = vendor_versions(
        {"data_vendors": {"core_stock_apis": "yfinance,sec_edgar"}}
    )

    assert versions["yfinance"] == importlib.metadata.version("yfinance")
    assert versions["sec_edgar"].startswith("tradingagents-")


def test_pit_coverage_covers_every_dated_path():
    coverage = pit_coverage()

    assert coverage == PIT_COVERAGE
    assert set(coverage) == {
        "price",
        "technical",
        "news",
        "macro",
        "fundamentals",
        "insider",
        "social",
        "identity",
        "memory",
    }
    assert all(coverage.values())


def test_cache_metrics_count_hits_misses_and_writes(tmp_path):
    metrics = CacheMetrics()
    cache = CacheController(tmp_path)
    key = CacheKey(data_class="news", source="test", subject="NVDA")

    with cache_metrics_scope(metrics):
        cache.get_or_fetch(key, lambda: "value")
        cache.get_or_fetch(key, lambda: "other")

    assert metrics.hits == 1
    assert metrics.misses == 1
    assert metrics.writes == 1
    assert metrics.as_dict()["hit_rate"] == 0.5


def test_fallback_metrics_summarize_typed_events():
    metrics = summarize_fallback_events(
        [
            FailureEvent(kind="source_failure", source="fred", message="x", action="unavailable"),
            FailureEvent(kind="llm_failure", source="deep", message="y", action="cheaper_model"),
            FailureEvent(kind="source_failure", source="reddit", message="z", action="unavailable"),
        ]
    )

    assert metrics["count"] == 3
    assert metrics["by_kind"] == {"source_failure": 2, "llm_failure": 1}
    assert metrics["by_action"] == {"unavailable": 2, "cheaper_model": 1}
