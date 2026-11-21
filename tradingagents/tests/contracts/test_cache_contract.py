"""Contract validation for cache keys, entries and TTL policies."""
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from tradingagents.contracts.cache import CacheEntry, CacheKey, TTLPolicy


def test_cache_key_requires_identity_fields():
    with pytest.raises(ValidationError):
        CacheKey(data_class="price", source="yahoo")


def test_default_ttl_matrix():
    assert {name: TTLPolicy.for_data_class(name).seconds for name in
            ("price", "technical", "news", "social", "fundamental", "identity")} == {
                "price": 900, "technical": 900, "news": 3600,
                "social": 3600, "fundamental": 86400, "identity": 604800,
            }
    assert TTLPolicy.for_request("price", market_open=False).seconds == 86400


def test_entry_expiry_boundary_is_exclusive():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    entry = CacheEntry(value="x", expires_at=now + timedelta(seconds=30))
    assert entry.is_fresh(now + timedelta(seconds=29))
    assert not entry.is_fresh(now + timedelta(seconds=30))
