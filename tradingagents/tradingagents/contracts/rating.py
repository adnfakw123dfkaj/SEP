"""Rating contracts shared across the pipeline (Part 5).

The committed rating is the single authoritative value produced by the
deterministic validator in :mod:`tradingagents.agents.rating`. LLM output is
advisory: it is a *candidate* that the authority checks before it may be stored.

This module defines the wire/contract objects only; the commit logic lives in
:mod:`tradingagents.rating_authority` (which re-uses the parser in
:mod:`tradingagents.agents.rating`). Keeping the contract separate lets Part 3
(manifest/report) and Part 6 (cost) read a stable shape without importing the
authority itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The committed value is exactly one of these six. Anything else is invalid.
ALLOWED_RATINGS: frozenset[str] = frozenset(
    {"Buy", "Overweight", "Hold", "Underweight", "Sell", "REVIEW"}
)

# The tradeable subset (REVIEW is a "needs human/re-run" signal, not a position).
TRADEABLE_RATINGS: frozenset[str] = ALLOWED_RATINGS - {"REVIEW"}

REVIEW: str = "REVIEW"


# Reason codes attached to a RatingResult. They are stable identifiers so tests,
# logs and downstream tooling can assert *why* a decision is (or is not) REVIEW.
class ReasonCode:
    """Machine-readable reasons for a rating outcome."""

    OK = "ok"
    # The candidate text had no readable rating.
    NO_RATING = "no_rating"
    # The candidate string was not in the allowed set.
    OUT_OF_SET = "out_of_set"
    # A required provenance field was missing or empty.
    MISSING_PROVENANCE = "missing_provenance"
    # A provenance field was present but did not validate (bad id/version shape).
    INVALID_PROVENANCE = "invalid_provenance"
    # The snapshot id was absent or not marked verified.
    UNVERIFIED_SNAPSHOT = "unverified_snapshot"
    # The same decision id was already committed with a different value.
    CONFLICT = "conflict"
    # The persisted value failed re-validation before write.
    PERSISTED_OUT_OF_SET = "persisted_out_of_set"


def is_allowed(rating: str) -> bool:
    """Whether ``rating`` is one of the six allowed committed values."""
    return rating in ALLOWED_RATINGS


def coerce_review(reason_code: str, *, provenance: Any = None) -> RatingResult:
    """A REVIEW result carrying ``reason_code`` (never a tradeable tier)."""
    return RatingResult(
        rating=REVIEW,
        reason_codes=(reason_code,),
        provenance=provenance,
        review_required=True,
    )


@dataclass(frozen=True)
class RatingResult:
    """The outcome of rating resolution / commit.

    Fields (the agreed contract; extra fields may be added, existing ones are
    never repurposed):

    - ``rating``: exactly one of :data:`ALLOWED_RATINGS`. This is the only value
      that may be persisted as the decision's rating.
    - ``reason_codes``: stable codes (see :class:`ReasonCode`) explaining the
      outcome; ``("ok",)`` for a clean tradeable commit.
    - ``provenance``: the verified :class:`Provenance` this result was produced
      from, or ``None`` when provenance was missing/invalid. Never free text.
    - ``review_required``: ``True`` iff the value must not be treated as a
      position (i.e. ``rating == "REVIEW"``). Redundant with the rating by
      design, so callers can branch on intent without string compares.

    Added field:

    - ``decision_id``: the stable id the commit was keyed on (for idempotency),
      or ``None`` for a resolution that was not stored.
    """

    rating: str
    reason_codes: tuple[str, ...] = (ReasonCode.OK,)
    provenance: Provenance | None = None
    review_required: bool = False
    decision_id: str | None = None

    def __post_init__(self) -> None:
        if self.rating not in ALLOWED_RATINGS:
            raise ValueError(f"rating {self.rating!r} is not in the allowed set")
        # Keep the contract self-consistent: REVIEW <=> review_required.
        if (self.rating == REVIEW) != bool(self.review_required):
            raise ValueError(
                "review_required must be True exactly when rating is REVIEW"
            )

    @property
    def is_tradeable(self) -> bool:
        return self.rating in TRADEABLE_RATINGS

    @property
    def is_review(self) -> bool:
        return self.rating == REVIEW


@dataclass(frozen=True)
class Provenance:
    """Verified provenance a commit must carry.

    A commit is only allowed when every field is present *and* validates. These
    are structural ids/versions, not arbitrary non-empty strings: the ids must
    match their hex/uuid-ish shape and versions must be non-empty with a
    recognisable version token. Production populates this from the run's real
    snapshot/manifest/models; tests use a clearly-marked fake (see
    :class:`Provenance` construction in the authority's in-memory tests).

    Fields:

    - ``snapshot_id``: the verified market snapshot id, e.g. ``snap-<32 hex>``.
    - ``manifest_id``: the evidence manifest id for this run, e.g. ``man-<32 hex>``.
    - ``model``: the model identifier used for the decision.
    - ``prompt_version``: the prompt template version pin.
    - ``config_version``: the config version pin.

    Additional:

    - ``snapshot_verified``: whether the snapshot was cryptographically/structurally
      verified. An unverified snapshot id is not acceptable for a commit.
    """

    snapshot_id: str
    manifest_id: str
    model: str
    prompt_version: str
    config_version: str
    snapshot_verified: bool = True

    def missing_fields(self) -> list[str]:
        """Names of required fields that are empty/missing."""
        required = (
            "snapshot_id",
            "manifest_id",
            "model",
            "prompt_version",
            "config_version",
        )
        return [name for name in required if not getattr(self, name)]


# Store adapter protocol (Part 5 owns the write-gate; the concrete store is
# provided by Part 3). A store is any object exposing these two methods. The
# authority never assumes more than this.
#
#   read(decision_id: str) -> dict | None
#       returns the previously stored record (must include a "rating" key) or
#       None when nothing is stored for ``decision_id``.
#   write(decision_id: str, record: dict) -> None
#       persists ``record`` for ``decision_id``; must be atomic for that id.
#
# The authority re-validates the rating immediately before calling ``write`` and
# refuses an out-of-set value (never trusting the store).
Store = Any


@dataclass
class InMemoryRatingStore:
    """A minimal in-memory store used by tests and as the reference adapter.

    It is deliberately tiny: Part 3's real records store is expected to be
    dropped in behind the same ``read``/``write`` interface.
    """

    _records: dict[str, dict] = field(default_factory=dict)

    def read(self, decision_id: str) -> dict | None:
        return self._records.get(decision_id)

    def write(self, decision_id: str, record: dict) -> None:
        self._records[decision_id] = dict(record)

    def all(self) -> dict[str, dict]:
        return dict(self._records)
