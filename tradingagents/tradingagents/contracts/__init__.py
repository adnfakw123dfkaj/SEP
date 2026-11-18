"""Shared data contracts (Part 5 owns the rating contract; other parts add theirs).

Only the rating contract lives here today. Importing this package must stay
cheap and side-effect free so the safety-path contract check
(``scripts/gates/run_static_checks.py::check_contract``) can import every
``contracts/*.py`` module cleanly.
"""

from __future__ import annotations

from .rating import (
    ALLOWED_RATINGS,
    REVIEW,
    TRADEABLE_RATINGS,
    InMemoryRatingStore,
    Provenance,
    RatingResult,
    ReasonCode,
    coerce_review,
    is_allowed,
)

__all__ = [
    "ALLOWED_RATINGS",
    "REVIEW",
    "TRADEABLE_RATINGS",
    "InMemoryRatingStore",
    "Provenance",
    "RatingResult",
    "ReasonCode",
    "coerce_review",
    "is_allowed",
]
