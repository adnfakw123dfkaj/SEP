#!/usr/bin/env python3
"""Measure local preflight latency for a real ticker (provider access required)."""
import argparse
import statistics
import time

from tradingagents.preflight import validate_request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--assert-p95", type=float, help="Maximum p95 latency in seconds (e.g. 2)")
    args = parser.parse_args()
    samples = []
    for _ in range(args.runs):
        start = time.perf_counter()
        result = validate_request(args.ticker)
        samples.append(time.perf_counter() - start)
        if not result.ok:
            parser.error(f"preflight failed: {result.reason}")
    ordered = sorted(samples)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
    print(f"ticker={args.ticker} runs={args.runs} p50_s={statistics.median(samples):.3f} p95_s={p95:.3f}")
    if args.assert_p95 is not None and p95 > args.assert_p95:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
