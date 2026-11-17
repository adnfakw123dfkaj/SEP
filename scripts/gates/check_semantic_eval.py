"""Gate 4 — Semantic evaluation gate (PDF §6.4).

For any prompt or model change, the pipeline replays a fixed evaluation set
against quality thresholds before the change can reach production; a failed
threshold blocks and is reported.

This script holds the *classification* and *threshold* logic:

- classify whether a change is eval-relevant (touches prompts or model config);
- given the metrics the offline harness measured on the fixed set, decide pass or
  block, naming every threshold that failed.

The heavy lifting (running the fixed set through a model) is the harness's job
and is offline/deterministic; this module only judges its numbers.
"""

from __future__ import annotations

from common import GateResult, Violation

# A change is eval-relevant if it touches any of these trees/files.
PROMPT_MODEL_PATHS = ("prompts/",)
PROMPT_MODEL_SUFFIXES = ("_analyst.py", "prompts.py")
# Config keys whose change means a model change.
MODEL_CONFIG_KEYS = {
    "deep_think_llm", "quick_think_llm", "deep_think_provider", "quick_think_provider",
    "llm_provider", "temperature", "max_tokens",
    "google_thinking_level", "openai_reasoning_effort", "anthropic_effort",
}

# Thresholds on the fixed evaluation set. Direction matters: "min" metrics must
# be >= the threshold; "max" metrics must be <=.
THRESHOLDS = {
    "faithfulness": (0.80, "min"),
    "relevance": (0.80, "min"),
    "numeric_consistency": (0.98, "min"),
    "review_rate": (0.02, "max"),
}


def is_eval_relevant(changed_files: list[str], changed_config_keys: list[str] | None = None) -> bool:
    """Whether this change touches a prompt or model setting."""
    for path in changed_files:
        normalized = path.lstrip("./")
        if any(normalized.startswith(p) for p in PROMPT_MODEL_PATHS):
            return True
        if normalized.endswith(PROMPT_MODEL_SUFFIXES):
            return True
    return bool(changed_config_keys) and bool(set(changed_config_keys) & MODEL_CONFIG_KEYS)


def check(
    changed_files: list[str],
    metrics: dict[str, float] | None,
    changed_config_keys: list[str] | None = None,
) -> GateResult:
    """Evaluate the semantic-evaluation gate.

    Args:
        changed_files: every path the change touches.
        metrics: the fixed-set metrics the harness measured, or None if the
            harness did not run.
        changed_config_keys: config keys changed by the PR (for model changes).
    """
    result = GateResult(gate="G4")
    if not is_eval_relevant(changed_files, changed_config_keys):
        result.applicable = False
        return result

    if metrics is None:
        result.violations.append(
            Violation("evaluation not run", "prompt/model change without a fixed-set replay")
        )
        return result

    for name, (threshold, direction) in THRESHOLDS.items():
        if name not in metrics:
            result.violations.append(Violation("metric missing", name))
            continue
        value = metrics[name]
        if direction == "min" and value < threshold:
            result.violations.append(
                Violation("threshold failed", f"{name}={value:.3f} < {threshold}")
            )
        elif direction == "max" and value > threshold:
            result.violations.append(
                Violation("threshold failed", f"{name}={value:.3f} > {threshold}")
            )
    return result
