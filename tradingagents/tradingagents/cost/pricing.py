"""Official DeepSeek CNY price table for Part 6.

Source: https://api-docs.deepseek.com/zh-cn/quick_start/pricing/
Retrieved: 2026-11-16.  Prices are CNY per million tokens.  Cache pricing is
modelled as cache-miss only, per the agreed policy.
"""

from datetime import date
from decimal import Decimal

from tradingagents.contracts.cost import ModelPrice, PricePair, PriceTable

_SOURCE_URL = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
_RETRIEVED_AT = date(2026, 11, 16)


def default_price_table() -> PriceTable:
    """Return the versioned price table used by real acceptance runs."""
    return PriceTable(
        currency="CNY",
        version="deepseek-cny-2026-11-16",
        source_url=_SOURCE_URL,
        retrieved_at=_RETRIEVED_AT,
        models={
            "deepseek-flash": ModelPrice(
                model="deepseek-flash",
                model_version="DeepSeek-V4.1-Flash-1017",
                peak=PricePair(
                    input_cache_miss_per_1m=Decimal("2"),
                    output_per_1m=Decimal("8"),
                ),
                off_peak=PricePair(
                    input_cache_miss_per_1m=Decimal("1"),
                    output_per_1m=Decimal("4"),
                ),
            ),
            "deepseek-v4-pro": ModelPrice(
                model="deepseek-v4-pro",
                model_version="DeepSeek-V4-Pro-0813",
                peak=PricePair(
                    input_cache_miss_per_1m=Decimal("9"),
                    output_per_1m=Decimal("27"),
                ),
                off_peak=PricePair(
                    input_cache_miss_per_1m=Decimal("4.5"),
                    output_per_1m=Decimal("13.5"),
                ),
            ),
        },
    )
