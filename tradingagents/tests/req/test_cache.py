"""Behavior checks for Part 4 local cache."""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Lock

from tradingagents.cache import CacheController
from tradingagents.contracts.cache import CacheKey, TTLPolicy


def test_hit_rate(tmp_path):
    cache = CacheController(tmp_path)
    key = CacheKey(data_class="news", source="test", subject="AAPL", as_of="2026-01-01")
    calls = 0

    def fetch():
        nonlocal calls
        calls += 1
        return {"headline": "example"}, {"source": "fixture"}

    for _ in range(10):
        cache.get_or_fetch(key, fetch)
    assert calls == 1
    assert cache.get(key).provenance == {"source": "fixture"}


def test_no_stale(tmp_path):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    cache = CacheController(tmp_path, TTLPolicy(seconds=60))
    key = CacheKey(data_class="news", source="test", subject="AAPL")
    cache.set(key, "fresh", now=now)
    assert cache.get(key, now=now + timedelta(seconds=59)).value == "fresh"
    assert cache.get(key, now=now + timedelta(seconds=60)) is None


def test_default_ttls():
    assert TTLPolicy.for_data_class("price").seconds == 900
    assert TTLPolicy.for_data_class("news").seconds == 3600
    assert TTLPolicy.for_data_class("identity").seconds == 604800


def test_concurrent_get_or_fetch_only_fetches_once(tmp_path):
    cache = CacheController(tmp_path)
    key = CacheKey(data_class="news", source="test", subject="AAPL")
    lock, calls = Lock(), [0]

    def fetch():
        with lock:
            calls[0] += 1
        time.sleep(0.03)
        return "shared"

    with ThreadPoolExecutor(max_workers=8) as pool:
        entries = list(pool.map(lambda _i: cache.get_or_fetch(key, fetch), range(8)))
    assert calls == [1]
    assert {entry.value for entry in entries} == {"shared"}
