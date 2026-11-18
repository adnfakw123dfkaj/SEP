"""Security regression harness (Part 5, REQ-SEC-001 cases 01–03).

Runs the deterministic Part 5 sanitisation + rating-authority chain over the
committed security fixtures and reports the metrics the requirement names. All
metrics are computed from the run; nothing is hard-coded.

Usage:
  python scripts/security_regression.py --injections 200 --assert-block-rate 0.99
  python scripts/security_regression.py --benign 200 --assert-fp 0.05
  python scripts/security_regression.py --assert-influence 0
  python scripts/security_regression.py --all            # run every check

Exit code 0 iff every requested assertion holds.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "tradingagents"
FIXTURES = PKG / "tests" / "fixtures" / "security"
sys.path.insert(0, str(PKG))

from tradingagents.contracts.rating import InMemoryRatingStore, Provenance
from tradingagents.rating_authority import commit_rating
from tradingagents.security import (
    is_suspicious,
    reset_event_log,
    sanitize,
)
from tradingagents.security.sanitize import sanitize_detailed


def _load(name: str) -> list[str]:
    path = FIXTURES / name
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.strip()]


def _prov() -> Provenance:
    return Provenance(
        snapshot_id="snap-0123abcd4567ef890123abcd4567ef89",
        manifest_id="man-fedcba9876543210fedcba9876543210",
        model="deepseek-chat",
        prompt_version="v1.2.0",
        config_version="v3.0.1",
    )


def block_rate(limit: int) -> float:
    payloads = _load("injections.txt")[:limit]
    reset_event_log()
    blocked = 0
    for p in payloads:
        out = sanitize_detailed(p)
        if out.dropped or not is_suspicious(out.retained):
            blocked += 1
    return blocked / len(payloads)


def false_positive_rate(limit: int) -> float:
    benign = _load("benign.txt")[:limit]
    reset_event_log()
    dropped = 0
    for line in benign:
        if sanitize_detailed(line).dropped:
            dropped += 1
    return dropped / len(benign)


def influence_count() -> int:
    """How many sanitised fetched fields are accepted as a changed rating.

    A fixed structured decision is the control. Each injection is sanitised (the
    real chain); if the sanitised field survives AND is accepted as a committed
    rating different from the control, it counts as an influence (must be 0).
    The reverse (raw, un-sanitised) acceptance is reported separately by
    ``raw_would_flip`` so the result is provably not vacuous.
    """
    control_text = "**Rating**: Hold\n\nBalanced risk/reward."
    control = commit_rating(control_text, _prov(), InMemoryRatingStore(),
                            decision_id="control")
    influenced = 0
    for i, payload in enumerate(_load("injections.txt")):
        fetched = sanitize(payload)  # what would reach the prompt
        if not fetched:
            continue
        result = commit_rating(fetched, _prov(), InMemoryRatingStore(),
                               decision_id=f"t{i}")
        if result.rating != control.rating:
            influenced += 1
    return influenced


def raw_would_flip() -> int:
    """Control metric: payloads a *broken* (no-sanitise) pipeline would accept.

    Non-zero proves the influence check is not vacuous.
    """
    count = 0
    for payload in _load("injections.txt"):
        result = commit_rating(payload, _prov(), InMemoryRatingStore(),
                              decision_id="raw")
        if result.rating != "REVIEW":
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--injections", type=int, default=None)
    parser.add_argument("--benign", type=int, default=None)
    parser.add_argument("--assert-block-rate", type=float, default=None)
    parser.add_argument("--assert-fp", type=float, default=None)
    parser.add_argument("--assert-influence", type=int, default=None)
    parser.add_argument("--all", action="store_true", help="run every check")
    args = parser.parse_args(argv)

    failures: list[str] = []

    if args.all:
        args.injections = args.injections or 200
        args.benign = args.benign or 200
        args.assert_block_rate = 0.99 if args.assert_block_rate is None else args.assert_block_rate
        args.assert_fp = 0.05 if args.assert_fp is None else args.assert_fp
        args.assert_influence = 0 if args.assert_influence is None else args.assert_influence

    if args.injections or args.assert_block_rate is not None:
        rate = block_rate(args.injections or len(_load("injections.txt")))
        print(f"injection_block_or_drop_rate={rate:.4f}")
        if args.assert_block_rate is not None and rate < args.assert_block_rate:
            failures.append(f"block rate {rate:.4f} < {args.assert_block_rate}")

    if args.benign or args.assert_fp is not None:
        rate = false_positive_rate(args.benign or len(_load("benign.txt")))
        print(f"benign_false_positive_rate={rate:.4f}")
        if args.assert_fp is not None and rate > args.assert_fp:
            failures.append(f"FP rate {rate:.4f} > {args.assert_fp}")

    if args.assert_influence is not None:
        count = influence_count()
        print(f"injected_influence_on_rating_count={count}")
        raw = raw_would_flip()
        print(f"raw_pipeline_would_accept_count={raw}  (control: must be > 0)")
        if count > args.assert_influence:
            failures.append(f"influence {count} > {args.assert_influence}")
        if raw == 0:
            failures.append("reverse control is vacuous: no raw payload would flip")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
