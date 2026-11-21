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


def _record_source(prov):
    """The source fields as they are persisted in a store record (incl. the
    persisted verification flag)."""
    return {
        "snapshot_id": prov.snapshot_id,
        "manifest_id": prov.manifest_id,
        "model": prov.model,
        "prompt_version": prov.prompt_version,
        "config_version": prov.config_version,
        "snapshot_verified": True,
    }


def test_file_rating_store_roundtrip(tmp_path):
    from tradingagents.records import FileRatingStore

    store = FileRatingStore(tmp_path)
    store.write("decision-1", {"rating": "Buy", "decision_id": "decision-1"})
    assert store.read("decision-1")["rating"] == "Buy"
    assert store.read("missing") is None


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
    """TC-P5-INV003-07: the commit gate is idempotent (serial)."""
    store = InMemoryRatingStore()
    prov = _provenance()
    first = commit_rating("**Rating**: Buy", prov, store, decision_id="same")
    second = commit_rating("**Rating**: Buy", prov, store, decision_id="same")
    assert first.rating == second.rating == "Buy"
    # A same-request retry returns the originally persisted source, reason ok.
    assert second.reason_codes == (ReasonCode.OK,)
    assert second.provenance == prov
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


def test_retry_returns_persisted_source():
    """A retry with the same request returns the *stored* provenance, not the
    request's object, and does not rewrite."""
    store = InMemoryRatingStore()
    original = _provenance()
    commit_rating("Buy", original, store, decision_id="r")
    before = dict(store.read("r"))
    # A second, equal-but-distinct provenance object (same fingerprint).
    retry = _provenance()
    result = commit_rating("Buy", retry, store, decision_id="r")
    assert result.rating == "Buy"
    assert result.reason_codes == (ReasonCode.OK,)
    # Returns the persisted source identity.
    assert result.provenance is not None
    assert result.provenance.fingerprint() == original.fingerprint()
    # Nothing was rewritten.
    assert store.read("r") == before


def test_conflicting_rating_is_rejected():
    """Different rating for an existing id -> CONFLICT, no overwrite."""
    store = InMemoryRatingStore()
    prov = _provenance()
    commit_rating("Buy", prov, store, decision_id="c")
    before = dict(store.read("c"))
    result = commit_rating("Sell", prov, store, decision_id="c")
    assert result.rating == RATING_REVIEW
    assert result.review_required
    assert ReasonCode.CONFLICT in result.reason_codes
    assert store.read("c") == before  # not overwritten


def test_conflicting_source_is_rejected():
    """Same rating but a different source for an existing id -> CONFLICT."""
    store = InMemoryRatingStore()
    commit_rating("Hold", _provenance(), store, decision_id="s")
    before = dict(store.read("s"))
    # Different snapshot id => different source fingerprint.
    other_source = _provenance(snapshot_id="snap-ffffffffffffffffffffffffffffffff")
    result = commit_rating("Hold", other_source, store, decision_id="s")
    assert result.rating == RATING_REVIEW
    assert ReasonCode.CONFLICT in result.reason_codes
    assert store.read("s") == before


def test_missing_source_retry_is_not_success():
    """Retrying an existing id with no provenance is not a normal success."""
    store = InMemoryRatingStore()
    commit_rating("Buy", _provenance(), store, decision_id="m")
    before = dict(store.read("m"))
    result = commit_rating("Buy", None, store, decision_id="m")
    # Not reason=ok; the missing source cannot be silently accepted.
    assert ReasonCode.OK not in result.reason_codes
    assert result.review_required
    assert store.read("m") == before


def _assert_fail_closed(result, store, decision_id, reason=None):
    """A refused outcome must be REVIEW, require review, be non-tradeable, and
    not have written anything for ``decision_id``."""
    assert result.rating == RATING_REVIEW
    assert result.review_required is True
    assert result.is_tradeable is False
    if reason is not None:
        assert reason in result.reason_codes, result.reason_codes
    # The stored record (if any) is not created/overwritten by the refusal.
    return store.read(decision_id)


def test_corrupt_record_is_classified_accurately():
    """Corrupt records fail closed: REVIEW / review_required / non-tradeable,
    with an accurate reason, and are never overwritten."""
    store = InMemoryRatingStore()
    prov = _provenance()
    # (a) out-of-set stored rating -> PERSISTED_OUT_OF_SET, source intact.
    store.write("bad-rating", {"rating": "Moon", "decision_id": "bad-rating",
                               **_record_source(prov)})
    before = dict(store.read("bad-rating"))
    r = commit_rating("Buy", prov, store, decision_id="bad-rating")
    stored = _assert_fail_closed(r, store, "bad-rating", ReasonCode.PERSISTED_OUT_OF_SET)
    assert stored == before  # not overwritten

    # (b) existing **Buy** record whose SOURCE FIELDS ARE MISSING must still be
    # REVIEW/non-tradeable (this was the defect: it used to surface Buy).
    store.write("bad-source", {"rating": "Buy", "decision_id": "bad-source"})
    before = dict(store.read("bad-source"))
    r = commit_rating("Buy", prov, store, decision_id="bad-source")
    stored = _assert_fail_closed(r, store, "bad-source", ReasonCode.CORRUPT_RECORD)
    assert ReasonCode.PERSISTED_OUT_OF_SET not in r.reason_codes
    assert store.read("bad-source")["rating"] == "Buy"  # untouched
    assert stored == before

    # (c) read-back classifies and fails closed the same way.
    back_a = read_committed_rating(store, decision_id="bad-rating")
    assert back_a.rating == RATING_REVIEW and back_a.is_tradeable is False
    assert ReasonCode.PERSISTED_OUT_OF_SET in back_a.reason_codes
    back_b = read_committed_rating(store, decision_id="bad-source")
    assert back_b.rating == RATING_REVIEW and back_b.is_tradeable is False
    assert ReasonCode.CORRUPT_RECORD in back_b.reason_codes


def test_corrupt_source_eventually_rejected_on_retry_and_readback():
    """A stored record whose source id/version format is invalid -> rejected on
    both read-back and retry; REVIEW / review_required / non-tradeable."""
    prov = _provenance()
    store = InMemoryRatingStore()
    bad = _record_source(prov)
    bad["snapshot_id"] = "not-a-snapshot-id"  # malformed id
    store.write("fmt", {"rating": "Buy", "decision_id": "fmt", **bad})
    before = dict(store.read("fmt"))

    back = read_committed_rating(store, decision_id="fmt")
    assert back.rating == RATING_REVIEW and back.review_required is True
    assert back.is_tradeable is False

    retry = commit_rating("Buy", prov, store, decision_id="fmt")
    assert retry.rating == RATING_REVIEW and retry.review_required is True
    assert retry.is_tradeable is False
    assert ReasonCode.CORRUPT_RECORD in retry.reason_codes
    assert store.read("fmt") == before  # not overwritten


def test_unverified_same_source_retry_is_rejected():
    """A retry whose REQUEST provenance is snapshot_verified=False is rejected
    even when its fingerprint matches the stored source."""
    store = InMemoryRatingStore()
    good = _provenance()
    commit_rating("Buy", good, store, decision_id="u")
    before = dict(store.read("u"))

    # Same source fields, but the request did not verify the snapshot.
    unverified = _provenance(snapshot_verified=False)
    result = commit_rating("Buy", unverified, store, decision_id="u")
    assert result.rating == RATING_REVIEW and result.review_required is True
    assert result.is_tradeable is False
    assert ReasonCode.UNVERIFIED_SNAPSHOT in result.reason_codes
    assert store.read("u") == before  # not rewritten


def test_decision_id_mismatch_is_rejected():
    """A stored record whose decision_id disagrees with the queried id is
    corrupt -> REVIEW, non-tradeable, not overwritten."""
    prov = _provenance()
    store = InMemoryRatingStore()
    store.write("q", {"rating": "Buy", "decision_id": "different", **_record_source(prov)})
    before = dict(store.read("q"))

    result = commit_rating("Buy", prov, store, decision_id="q")
    assert result.rating == RATING_REVIEW and result.review_required is True
    assert result.is_tradeable is False
    assert ReasonCode.CORRUPT_RECORD in result.reason_codes
    assert store.read("q") == before


def test_valid_commit_and_valid_retry_still_work():
    """Positive: a legitimate commit is tradeable and written; an identical
    *valid* retry returns the stored source without rewriting."""
    store = InMemoryRatingStore()
    prov = _provenance()

    first = commit_rating("**Rating**: Buy", prov, store, decision_id="ok")
    assert first.rating == "Buy"
    assert first.review_required is False
    assert first.is_tradeable is True
    written = dict(store.read("ok"))
    assert written["rating"] == "Buy"
    assert written["snapshot_verified"] is True

    retry = commit_rating("**Rating**: Buy", _provenance(), store, decision_id="ok")
    assert retry.rating == "Buy"
    assert retry.review_required is False
    assert retry.is_tradeable is True
    assert retry.reason_codes == (ReasonCode.OK,)
    assert retry.provenance is not None
    assert retry.provenance.fingerprint() == prov.fingerprint()
    assert store.read("ok") == written  # not rewritten
