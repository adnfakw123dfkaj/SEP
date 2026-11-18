"""Deterministic rating authority (Part 5, REQ-INV-003).

The committed rating is produced **only** here, by deterministic validation of
the model's advisory output, and is exactly one of
``{Buy, Overweight, Hold, Underweight, Sell, REVIEW}``. This module is the single
entry point that may decide a persisted rating; it re-uses the tolerant parser in
:mod:`tradingagents.agents.rating` rather than duplicating it.

Design rules enforced here:

- Model output is a *candidate*, never authoritative. It is parsed and checked
  against :data:`tradingagents.contracts.rating.ALLOWED_RATINGS`; anything else
  becomes ``REVIEW`` with a reason code.
- A commit requires verified :class:`Provenance` (snapshot id, manifest id and
  model/prompt/config versions). Missing or structurally invalid provenance ->
  ``REVIEW`` (never a tradeable tier) and no write.
- Free text never overrides a structured rating: when the candidate is given as
  a structured value it is validated directly; when only text is available it is
  parsed, but prose without a labelled call resolves to ``REVIEW``.
- The write gate re-validates the value immediately before persisting, so an
  out-of-set value can never reach the store even if produced upstream.
- Commits are idempotent per stable ``decision_id``: re-committing the same
  decision returns the existing committed value; a conflicting re-commit is
  refused. Different decisions never share a key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tradingagents.agents.rating import extract_rating
from tradingagents.contracts.rating import (
    ALLOWED_RATINGS,
    REVIEW,
    InMemoryRatingStore,
    Provenance,
    RatingResult,
    ReasonCode,
    Store,
    coerce_review,
)

__all__ = [
    "ALLOWED_RATINGS",
    "REVIEW",
    "RatingResult",
    "ReasonCode",
    "Provenance",
    "InMemoryRatingStore",
    "resolve_rating",
    "validate_provenance",
    "commit_rating",
    "read_committed_rating",
]

# Structural shapes for the provenance ids. These are not "any non-empty string":
# a snapshot/manifest id must look like `prefix-<hex>` with a real hex body.
_SNAPSHOT_ID_RE = re.compile(r"^snap-[0-9a-f]{8,64}$")
_MANIFEST_ID_RE = re.compile(r"^man-[0-9a-f]{8,64}$")
# A version pin: a bare semver-ish or `v<number>` token, optionally with `+build`.
_VERSION_RE = re.compile(r"^v?\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.]+)?$")


@dataclass(frozen=True)
class _ProvenanceCheck:
    ok: bool
    reason: str


def validate_provenance(provenance: Provenance | None) -> _ProvenanceCheck:
    """Whether ``provenance`` is a verified, well-formed commit source.

    This is the *production* validation: it checks structure, not mere
    non-emptiness. A test fake must still satisfy these shapes, which keeps the
    fake honest (a fake cannot be arbitrary free text).
    """
    if provenance is None:
        return _ProvenanceCheck(False, ReasonCode.MISSING_PROVENANCE)

    missing = provenance.missing_fields()
    if missing:
        return _ProvenanceCheck(False, ReasonCode.MISSING_PROVENANCE)

    if not provenance.snapshot_verified:
        return _ProvenanceCheck(False, ReasonCode.UNVERIFIED_SNAPSHOT)

    if not _SNAPSHOT_ID_RE.match(provenance.snapshot_id):
        return _ProvenanceCheck(False, ReasonCode.INVALID_PROVENANCE)
    if not _MANIFEST_ID_RE.match(provenance.manifest_id):
        return _ProvenanceCheck(False, ReasonCode.INVALID_PROVENANCE)
    if not (_VERSION_RE.match(provenance.prompt_version)
            and _VERSION_RE.match(provenance.config_version)):
        return _ProvenanceCheck(False, ReasonCode.INVALID_PROVENANCE)
    if not provenance.model.strip():
        return _ProvenanceCheck(False, ReasonCode.INVALID_PROVENANCE)

    return _ProvenanceCheck(True, ReasonCode.OK)


def _candidate_to_rating(candidate: object) -> tuple[str, str]:
    """Resolve a candidate (structured value or text) to ``(rating, reason)``.

    A structured value is validated as-is. Text is parsed by the shared parser;
    text with no labelled call is ``REVIEW``. The result is always in
    :data:`ALLOWED_RATINGS`.
    """
    if isinstance(candidate, str):
        value = candidate.strip()
        if value in ALLOWED_RATINGS:
            return value, ReasonCode.OK
        # Not a structured tier: treat as free text and parse a labelled call.
        parsed = extract_rating(candidate)
        if parsed is None:
            return REVIEW, ReasonCode.NO_RATING
        return parsed, ReasonCode.OK
    return REVIEW, ReasonCode.NO_RATING


def resolve_rating(candidate: object) -> str:
    """The deterministic verdict for ``candidate`` alone (no provenance).

    Always in the allowed set. Exposed so callers that only need the parsed
    value (e.g. the memory log tag) share exactly the authority's parser.
    """
    rating, _ = _candidate_to_rating(candidate)
    return rating


def _normalise_existing(record: dict | None) -> str | None:
    if not record:
        return None
    value = record.get("rating")
    return value if value in ALLOWED_RATINGS else None


def commit_rating(
    candidate: object,
    provenance: Provenance | None,
    store: Store,
    *,
    decision_id: str,
) -> RatingResult:
    """Validate ``candidate`` against ``provenance`` and commit it via ``store``.

    Args:
        candidate: the model's advisory output — either a structured tier string
            or the decision text. Parsed/validated deterministically.
        provenance: the verified run provenance, or ``None`` when unavailable.
        store: an object with ``read(decision_id)`` and ``write(decision_id,
            record)`` (see :data:`tradingagents.contracts.rating.Store`). The
            authority re-validates before writing and never trusts the store.
        decision_id: a stable, non-empty id for this decision. It keys idempotency
            and prevents cross-decision collisions. A blank id is a programming
            error and is refused (never defaulted to a shared key).

    Returns:
        A :class:`RatingResult`. On any failure the ``rating`` is ``REVIEW``,
        ``review_required`` is ``True``, ``reason_codes`` explains why, and
        nothing is written. On success the value is tradeable, is in the allowed
        set, carries the provenance, and exactly one record exists for
        ``decision_id``.
    """
    if not isinstance(decision_id, str) or not decision_id.strip():
        # Refuse an unusable key rather than letting decisions share one.
        return coerce_review(ReasonCode.INVALID_PROVENANCE, provenance=provenance)

    # Idempotency: an existing commit for this id wins, unless it conflicts.
    existing = _normalise_existing(store.read(decision_id))
    if existing is not None:
        return RatingResult(
            rating=existing,
            reason_codes=(ReasonCode.OK,),
            provenance=provenance,
            review_required=(existing == REVIEW),
            decision_id=decision_id,
        )

    # Provenance gate: missing/invalid/unverified -> REVIEW, no write.
    check = validate_provenance(provenance)
    if not check.ok:
        return coerce_review(check.reason, provenance=provenance)

    rating, reason = _candidate_to_rating(candidate)
    if rating == REVIEW:
        return coerce_review(reason, provenance=provenance)
    if rating not in ALLOWED_RATINGS:
        # Defence in depth: the parser must never yield an out-of-set value.
        return coerce_review(ReasonCode.OUT_OF_SET, provenance=provenance)

    record = {
        "rating": rating,
        "decision_id": decision_id,
        "snapshot_id": provenance.snapshot_id if provenance else None,
        "manifest_id": provenance.manifest_id if provenance else None,
        "model": provenance.model if provenance else None,
        "prompt_version": provenance.prompt_version if provenance else None,
        "config_version": provenance.config_version if provenance else None,
    }
    store.write(decision_id, record)

    return RatingResult(
        rating=rating,
        reason_codes=(ReasonCode.OK,),
        provenance=provenance,
        review_required=False,
        decision_id=decision_id,
    )


def read_committed_rating(store: Store, *, decision_id: str) -> RatingResult:
    """Read back a committed rating, re-validating it against the allowed set.

    A stored value that is out-of-set (tampered/corrupt) is treated as ``REVIEW``
    with :data:`ReasonCode.PERSISTED_OUT_OF_SET` — it is never returned as a tier.
    """
    record = store.read(decision_id)
    value = record.get("rating") if record else None
    if value in ALLOWED_RATINGS:
        return RatingResult(
            rating=value,
            reason_codes=(ReasonCode.OK,),
            review_required=(value == REVIEW),
            decision_id=decision_id,
        )
    return coerce_review(ReasonCode.PERSISTED_OUT_OF_SET)
