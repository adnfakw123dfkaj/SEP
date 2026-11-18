"""REQ-INV-003 — Deterministic rating authority (Part 5).

Traceable to test-cases/part5-security-rating.md TC-P5-INV003-01..07. The rating
vocabulary and parser in ``tradingagents.agents.rating`` are the shared parser;
the deterministic commit authority lives in ``tradingagents.rating_authority``
and is tested for real here (the commit gate is independent of the composition
root — Part 1 wires it in; these tests drive it directly).
"""

import random

from tradingagents.agents.rating import (
    RATING_REVIEW,
    RATINGS_5_TIER,
    extract_rating,
    is_review,
    parse_rating,
    run_rating,
)
from tradingagents.contracts.rating import (
    InMemoryRatingStore,
    Provenance,
    ReasonCode,
)
from tradingagents.rating_authority import (
    commit_rating,
    read_committed_rating,
    resolve_rating,
)

ALLOWED = set(RATINGS_5_TIER) | {RATING_REVIEW}


def _provenance(**overrides):
    """A *test fake* provenance that still satisfies the production shapes.

    The fake is deliberately a well-formed snapshot/manifest id + version pins so
    it cannot stand in for arbitrary free text; tests that check bypasses remove
    or corrupt a field explicitly.
    """
    values = {
        "snapshot_id": "snap-0123abcd4567ef890123abcd4567ef89",
        "manifest_id": "man-fedcba9876543210fedcba9876543210",
        "model": "deepseek-chat",
        "prompt_version": "v1.2.0",
        "config_version": "v3.0.1",
        "snapshot_verified": True,
    }
    values.update(overrides)
    return Provenance(**values)


def test_allowed_set():
    """TC-P5-INV003-02: a committed rating is always in the allowed set."""
    store = InMemoryRatingStore()
    cases = ["**Rating**: Buy", "Rating: Sell", "no rating here", "Rating: Underweight"]
    committed = []
    for i, text in enumerate(cases):
        result = commit_rating(text, _provenance(), store, decision_id=f"d{i}")
        committed.append(result.rating)
    # Clean decisions are tradeable; a decision with no call is REVIEW.
    assert committed[0] == "Buy"
    assert committed[1] == "Sell"
    assert committed[2] == RATING_REVIEW
    assert committed[3] == "Underweight"
    # Every committed value is exactly one of the six, and it is what was stored.
    assert set(committed) <= ALLOWED
    for i, value in enumerate(committed):
        if value == RATING_REVIEW:
            # A REVIEW decision is not a normal commit: nothing is persisted.
            assert store.read(f"d{i}") is None
        else:
            assert store.read(f"d{i}")["rating"] == value


def test_fuzz():
    """TC-P5-INV003-01: 10,000 mutated inputs never escape the allowed set."""
    random.seed(0)
    parts = ["Buy", "Sell", "Hold", "Overweight", "Underweight", "not a Sell",
             "Sell-ish", "BUY", "Ｓｅｌｌ", "review", "%^&", "**Rating**", ":",
             "Rating：", "Rating: **Sell**"]
    store = InMemoryRatingStore()
    prov = _provenance()
    escapes = 0
    for i in range(10_000):
        text = " ".join(random.choice(parts) for _ in range(random.randint(0, 5)))
        rating = resolve_rating(text)
        if rating not in ALLOWED:
            escapes += 1
        # Exercise the commit path too: whatever it yields must be in-set.
        result = commit_rating(text, prov, store, decision_id=f"f{i}")
        if result.rating not in ALLOWED:
            escapes += 1
    assert escapes == 0


def test_adversarial_text_cannot_flip():
    """TC-P5-INV003-04: prose arguing the opposite does not flip a labelled rating."""
    # An explicit opening "Rating: Sell" is the call, even if the prose says otherwise.
    text = "**Rating**: Sell\n\nThis is clearly NOT a Sell; I would actually Buy."
    assert extract_rating(text) == "Sell"
    # Through the authority: the committed value follows the labelled call.
    store = InMemoryRatingStore()
    result = commit_rating(text, _provenance(), store, decision_id="adv")
    assert result.rating == "Sell"


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
    store = InMemoryRatingStore()
    # No provenance at all.
    r = commit_rating("**Rating**: Buy", None, store, decision_id="p1")
    assert r.rating == RATING_REVIEW and r.review_required
    assert ReasonCode.MISSING_PROVENANCE in r.reason_codes
    # Provenance with a field removed: each missing field refuses the commit.
    for field in ("snapshot_id", "manifest_id", "model", "prompt_version", "config_version"):
        broken = _provenance(**{field: ""})
        r = commit_rating("**Rating**: Buy", broken, store, decision_id=f"p-{field}")
        assert r.rating == RATING_REVIEW, field
        assert ReasonCode.MISSING_PROVENANCE in r.reason_codes, field
    # Nothing was committed for any of the refused decisions.
    assert store.all() == {}


def test_requires_provenance_rejects_free_text_source():
    """A free-text/non-structural 'source' is invalid provenance, not accepted."""
    store = InMemoryRatingStore()
    # Non-hex ids and non-version pins must not pass as verified provenance.
    bad = _provenance(snapshot_id="my-snapshot", manifest_id="some manifest")
    r = commit_rating("**Rating**: Buy", bad, store, decision_id="bad-shape")
    assert r.rating == RATING_REVIEW
    assert ReasonCode.INVALID_PROVENANCE in r.reason_codes
    assert store.all() == {}


def test_missing_snapshot_review():
    """TC-P5-INV003-05: missing snapshot id yields REVIEW."""
    store = InMemoryRatingStore()
    r = commit_rating("**Rating**: Buy", _provenance(snapshot_id=""), store, decision_id="ms")
    assert r.rating == RATING_REVIEW
    assert r.review_required
    assert store.all() == {}
    # An id present but not verified is equally not committable.
    r2 = commit_rating("**Rating**: Buy", _provenance(snapshot_verified=False), store, decision_id="ms2")
    assert r2.rating == RATING_REVIEW
    assert ReasonCode.UNVERIFIED_SNAPSHOT in r2.reason_codes
    assert store.all() == {}


def test_persisted_revalidation():
    """TC-P5-INV003-06: persisted out-of-set values are rejected."""
    # The write gate re-validates: an out-of-set persisted value reads as REVIEW,
    # never as a tier, even if it was written by a faulty/older writer.
    store = InMemoryRatingStore()
    store.write("tampered", {"rating": "Moon", "decision_id": "tampered"})
    back = read_committed_rating(store, decision_id="tampered")
    assert back.rating == RATING_REVIEW
    assert ReasonCode.PERSISTED_OUT_OF_SET in back.reason_codes
    # A normal commit persists only an in-set value.
    r = commit_rating("**Rating**: Hold", _provenance(), store, decision_id="ok")
    assert r.rating == "Hold"
    assert store.read("ok")["rating"] in ALLOWED


def test_idempotent_commit():
    """TC-P5-INV003-07: the commit gate is idempotent."""
    store = InMemoryRatingStore()
    prov = _provenance()
    first = commit_rating("**Rating**: Buy", prov, store, decision_id="same")
    second = commit_rating("**Rating**: Buy", prov, store, decision_id="same")
    assert first.rating == second.rating == "Buy"
    # Exactly one committed record for the decision.
    assert list(store.all()) == ["same"]
    # A blank decision id is refused — decisions never share a default key.
    blank = commit_rating("**Rating**: Buy", prov, store, decision_id="  ")
    assert blank.rating == RATING_REVIEW
    assert store.read("") is None
    # A distinct id is an independent decision, not a collision.
    other = commit_rating("**Rating**: Sell", prov, store, decision_id="different")
    assert other.rating == "Sell"
    assert set(store.all()) == {"same", "different"}
