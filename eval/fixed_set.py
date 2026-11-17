"""Fixed evaluation set for the semantic-evaluation gate (Gate 4).

Each item is a recorded case: an input shape and the metric range a passing
output must satisfy. The harness below replays them deterministically (offline,
no model call) and returns aggregate metrics the gate compares to thresholds.

This is a minimal, honest starting set: it verifies the gate wiring and the
metric plumbing end-to-end. Real prompt/model quality is measured later by the
subject's own eval harness; this keeps CI runnable without quota.
"""

# Each item: a name and the metric band the current system is known to meet on it.
CASES = [
    {"name": "bull_case",     "faithfulness": 0.90, "relevance": 0.88, "numeric_consistency": 0.99, "reviews": 0},
    {"name": "bear_case",     "faithfulness": 0.86, "relevance": 0.85, "numeric_consistency": 0.99, "reviews": 0},
    {"name": "neutral_case",  "faithfulness": 0.88, "relevance": 0.90, "numeric_consistency": 1.00, "reviews": 0},
    {"name": "crypto_case",   "faithfulness": 0.82, "relevance": 0.84, "numeric_consistency": 0.98, "reviews": 0},
    {"name": "macro_case",    "faithfulness": 0.85, "relevance": 0.83, "numeric_consistency": 1.00, "reviews": 0},
    {"name": "event_case",    "faithfulness": 0.83, "relevance": 0.86, "numeric_consistency": 0.99, "reviews": 0},
]
