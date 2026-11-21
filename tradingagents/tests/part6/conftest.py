"""Shared fixtures for Part 6 performance/cost tests.

Imports are intentionally local so that pytest can still collect the test
modules and report one clear missing-module failure per file during the red
phase of TDD.
"""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest


@pytest.fixture
def shanghai():
    return ZoneInfo("Asia/Shanghai")


@pytest.fixture
def synthetic_price_table():
    from tradingagents.contracts.cost import ModelPrice, PricePair, PriceTable

    return PriceTable(
        currency="CNY",
        version="synthetic-v1",
        source_url="https://example.test/pricing",
        retrieved_at=date(2026, 11, 16),
        models={
            "model-a": ModelPrice(
                model="model-a",
                model_version="a-1",
                peak=PricePair(input_cache_miss_per_1m=Decimal("2"), output_per_1m=Decimal("8")),
                off_peak=PricePair(input_cache_miss_per_1m=Decimal("1"), output_per_1m=Decimal("4")),
            ),
            "model-b": ModelPrice(
                model="model-b",
                model_version="b-1",
                peak=PricePair(input_cache_miss_per_1m=Decimal("1"), output_per_1m=Decimal("4")),
                off_peak=PricePair(input_cache_miss_per_1m=Decimal("0.5"), output_per_1m=Decimal("2")),
            ),
        },
    )


@pytest.fixture
def budget():
    from tradingagents.contracts.cost import Budget

    return Budget(profile="test", soft_limit=80, hard_limit=100, currency="CNY")


@pytest.fixture
def make_event(shanghai):
    from tradingagents.contracts.llm_event import (
        CallStatus,
        LLMCallEvent,
        RoutePath,
        UsageSource,
    )

    def _make(**overrides):
        data = {
            "event_id": "event-1",
            "run_id": "run-1",
            "call_id": "call-1",
            "agent_name": "market",
            "model": "model-a",
            "provider": "test-provider",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "latency_ms": 100.0,
            "status": CallStatus.SUCCESS,
            "retry_count": 0,
            "route_path": RoutePath.DIRECT,
            "usage_source": UsageSource.PROVIDER,
            "timestamp": datetime(2026, 11, 16, 10, 0, tzinfo=shanghai),
            "cache_hit": False,
            "tool_name": "tool-x",
        }
        data.update(overrides)
        return LLMCallEvent(**data)

    return _make


@pytest.fixture
def profile_config():
    return SimpleNamespace(
        name="quick",
        soft_token_limit=1234,
        hard_token_limit=25000,
    )
