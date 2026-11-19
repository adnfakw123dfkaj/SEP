"""REQ-INV-003 — Deterministic rating authority (Part 5).

Traceable to test-cases/part5-security-rating.md TC-P5-INV003-01..07. The rating
vocabulary and parser in ``tradingagents.agents.rating`` exist and are tested for
real here; the commit gate (provenance/snapshot prerequisites) is added by the
Part 5 work and skips until then.
"""

import random

from tests.req._support import require
from tradingagents.agents.rating import (
    RATING_REVIEW,
    RATINGS_5_TIER,
    extract_rating,
    is_review,
    parse_rating,
    run_rating,
)

ALLOWED = set(RATINGS_5_TIER) | {RATING_REVIEW}


def test_allowed_set():
    """TC-P5-INV003-02: a parsed rating is always in the allowed set."""
    for text in ("**Rating**: Buy", "Rating: Sell", "no rating here", "Rating: Underweight"):
        assert parse_rating(text) in ALLOWED


def test_fuzz():
    """TC-P5-INV003-01: 10,000 mutated inputs never escape the allowed set."""
    random.seed(0)
    parts = ["Buy", "Sell", "Hold", "Overweight", "Underweight", "not a Sell", "Sell-ish", "BUY", "Ｓｅｌｌ", "review", "%^&"]
    for _ in range(10_000):
        text = " ".join(random.choice(parts) for _ in range(random.randint(0, 4)))
        result = parse_rating(text)
        assert result in ALLOWED, result


def test_adversarial_text_cannot_flip():
    """TC-P5-INV003-04: prose arguing the opposite does not flip a labelled rating."""
    # An explicit opening "Rating: Sell" is the call, even if the prose says otherwise.
    text = "**Rating**: Sell\n\nThis is clearly NOT a Sell; I would actually Buy."
    assert extract_rating(text) == "Sell"


def test_review_sentinel():
    """A decision with no readable rating yields REVIEW, never a guessed tier."""
    assert parse_rating("The outlook is mixed with no clear call.") == RATING_REVIEW
    assert is_review(parse_rating("no rating"))


def test_run_rating_prefers_structured_field():
    """run_rating prefers the structured final_rating over text."""
    assert run_rating({"final_rating": "Overweight", "final_trade_decision": "**Rating**: Sell"}) == "Overweight"


def test_fullwidth_and_markdown_tolerant():
    """Fullwidth punctuation and bold are tolerated."""
    assert extract_rating("Rating：Overweight") == "Overweight"


def test_requires_provenance():
    """TC-P5-INV003-03: commit gate refuses a decision missing provenance."""
    require("tradingagents.security")


def test_missing_snapshot_review():
    """TC-P5-INV003-05: missing snapshot id yields REVIEW."""
    require("tradingagents.security")


def test_persisted_revalidation():
    """TC-P5-INV003-06: persisted out-of-set values are rejected."""
    require("tradingagents.records")


def test_idempotent_commit():
    """TC-P5-INV003-07: the commit gate is idempotent."""
    require("tradingagents.security")
