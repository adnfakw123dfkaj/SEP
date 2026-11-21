"""Behavior checks for Part 4 failure routing."""
from datetime import UTC, datetime, timedelta

from tradingagents.cache import CacheController
from tradingagents.contracts.cache import CacheKey
from tradingagents.resilience import (
    FallbackLLM,
    FallbackRouter,
    RetryPolicy,
    fallback_event_scope,
)


def test_no_fabrication(tmp_path):
    result = FallbackRouter().route(RuntimeError("offline"), {"source": "feed"})
    assert not result.available
    assert result.status == "review"
    assert "DATA_UNAVAILABLE" in result.value
    assert result.events[0].action == "unavailable"


def test_typed_events(tmp_path):
    cache = CacheController(tmp_path)
    key = CacheKey(data_class="news", source="feed", subject="AAPL")
    cache.set(key, "cached")
    result = FallbackRouter().route(RuntimeError("offline"), {"cache": cache, "key": key})
    assert result.available and result.value == "cached"
    assert result.events[0].kind == "source_failure"


def test_expired_cache_is_never_used_as_fallback(tmp_path):
    cache = CacheController(tmp_path)
    key = CacheKey(data_class="news", source="feed", subject="AAPL")
    old = datetime.now(UTC) - timedelta(hours=2)
    cache.set(key, "old-value", now=old)
    result = FallbackRouter().route(RuntimeError("offline"), {"cache": cache, "key": key})
    assert not result.available
    assert "old-value" not in result.value


def test_llm_failure_uses_the_quick_model():
    class Primary:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("primary down")

    class Quick:
        def invoke(self, *args, **kwargs):
            return "quick response"

    events = []
    with fallback_event_scope(events):
        result = FallbackLLM(Primary(), Quick()).invoke("prompt")

    assert result == "quick response"
    assert events[0].action == "cheaper_model"


def test_structured_llm_failure_uses_the_quick_model():
    class Structured:
        def __init__(self, value):
            self.value = value

        def invoke(self, *args, **kwargs):
            if self.value is None:
                raise RuntimeError("structured down")
            return self.value

    class Primary:
        def with_structured_output(self, *args, **kwargs):
            return Structured(None)

    class Quick:
        def with_structured_output(self, *args, **kwargs):
            return Structured({"rating": "Hold"})

    result = FallbackLLM(Primary(), Quick()).with_structured_output(dict).invoke("prompt")
    assert result == {"rating": "Hold"}


def test_llm_failure_degrade():
    attempts = 0

    def fail():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("offline")

    result = FallbackRouter(RetryPolicy(attempts=3)).fetch(fail, {})
    assert attempts == 3
    assert result.status == "review"
