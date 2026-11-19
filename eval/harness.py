"""Offline harness for the semantic-evaluation gate (Gate 4).

``run_fixed_set()`` replays the recorded fixed set and returns the aggregate
metrics the gate checks. It is deterministic and offline: it reads the recorded
per-case scores rather than calling a model, so CI can gate on it without quota.

When the subject has a real model-driven evaluator, it replaces the per-case
score source behind this same function; the gate's threshold logic is unchanged.
"""

from __future__ import annotations

try:
    from eval.fixed_set import CASES
except ModuleNotFoundError:  # run from the repo root without a package path
    from fixed_set import CASES


def run_fixed_set() -> dict[str, float]:
    """Aggregate metrics over the fixed set.

    Returns mean faithfulness, mean relevance, min numeric consistency, and the
    fraction of cases flagged for review.
    """
    n = len(CASES)
    if n == 0:
        return {"faithfulness": 0.0, "relevance": 0.0, "numeric_consistency": 0.0, "review_rate": 1.0}
    return {
        "faithfulness": sum(c["faithfulness"] for c in CASES) / n,
        "relevance": sum(c["relevance"] for c in CASES) / n,
        "numeric_consistency": min(c["numeric_consistency"] for c in CASES),
        "review_rate": sum(1 for c in CASES if c["reviews"]) / n,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_fixed_set(), indent=2))
