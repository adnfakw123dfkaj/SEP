# Blocking-gate scripts

Decision logic for the six blocking gates (PDF §6), callable offline and used by
the CI workflows. Each gate is a pure function in `check_*.py` returning a
`GateResult`; `run.py` is the CLI the workflow calls and `common.py` holds the
shared result model.

| File | Gate |
|---|---|
| `check_test_approval.py` | G1 — test approval (tests approved before implementation) |
| `check_static_analysis.py` | G2 — static analysis (always-on + safety-path checks) |
| `check_schema.py` | G3 — requirements registry schema |
| `check_semantic_eval.py` | G4 — semantic evaluation on prompt/model change |
| `check_regression.py` | G5 — regression over prior suites |
| `check_ai_use_log.py` | G6 — AI-use log updated with code/prompt changes |
| `check_ownership.py` | G7 — a claimed Part's tests must not skip or fail |

## Two layers (warn-only vs blocking)

The same scripts serve both layers. The caller decides severity via `--warn-only`:

- **Layer 1 — branch self-check**: `--warn-only`. Violations are reported but the
  process exits 0 (never blocks).
- **Layer 2 — PR to master**: no flag. A failed gate exits 1 and blocks the merge.

## CLI

```bash
python scripts/gates/run.py g5 --input in.json            # blocking
python scripts/gates/run.py g5 --input in.json --warn-only  # layer 1
```

`in.json` holds the keyword arguments for that gate's `check()`; stdout is the
JSON report, stderr the human summary, exit code the decision.

## Tests

`tests/gates/` verifies every gate's pass/block behaviour offline (no network, no
GitHub). Run: `python -m pytest tests/gates -q`.
