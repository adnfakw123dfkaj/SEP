# Bug Diary

One entry per significant bug: symptom, reproduction, classification, root cause,
fix, and which invariant gap it exposed.

## BUG-001 — CI G2 "dependencies" failed only in CI, not locally
- **Symptom**: `gate-static-analysis` reported `check failed: dependencies` on the
  runner though local runs passed.
- **Reproduction**: from repo root, `import tradingagents` resolves to the project
  directory as a namespace package (no `__version__`), then is cached in
  `sys.modules`, shadowing the real package.
- **Classification**: environment/import path defect (false-negative local).
- **Root cause**: `run_static_checks.check_dependencies` relied on importing
  `tradingagents` with cwd on `sys.path`.
- **Fix**: inspect `tradingagents/tradingagents/__init__.py` on disk (parses,
  declares `__version__`), cwd- and import-cache-independent.
- **Invariant gap**: none of REQ-INV-* directly; it was a gate correctness gap
  (a gate that fails for the wrong reason erodes trust). Related: G2 policy.

## BUG-002 — G1 blocked on gate-infrastructure tests
- **Symptom**: a PR touching `tests/gates/test_static_checks.py` was blocked with
  `approval does not cover changed tests`.
- **Reproduction**: change a gate self-test + app code; G1 required an approval
  listing the gate test.
- **Classification**: gate policy over-reach.
- **Root cause**: `test_changed` included `tests/gates/**`, which are gate tooling,
  not application tests.
- **Fix**: exclude `_GATE_INFRA_PREFIXES` (`scripts/gates/`, `tests/gates/`) from
  approval coverage (mirrors the code-side exemption).
- **Invariant gap**: none; policy alignment for G1.

## BUG-003 — G6 collector parsed YAML as JSON
- **Symptom**: `gate-ai-use-log` crashed with `JSONDecodeError` when reading
  `docs/ai-use-log.yaml`.
- **Reproduction**: run `collect_context.py log-entries`.
- **Classification**: parsing defect.
- **Root cause**: `new_log_entries` used `json.loads` on a YAML file.
- **Fix**: parse with `yaml.safe_load` (with a JSON/mini fallback when PyYAML is
  absent), and make the jobs `pip install pyyaml`.
- **Invariant gap**: none; G6 correctness.

## BUG-004 — G4 crashed on non-eval changes
- **Symptom**: `gate-semantic-eval` raised `TypeError: missing 'metrics'`.
- **Reproduction**: a PR that does not touch prompts/models.
- **Classification**: signature/dispatch defect.
- **Root cause**: `check(changed_files, metrics)` had no default and the workflow
  omitted `metrics` for non-eval changes.
- **Fix**: `metrics: ... | None = None`; workflow always writes `metrics`.
- **Invariant gap**: none; G4 correctness.

## BUG-005 — G5 baseline vs parameter-id drift
- **Symptom**: G5 reported a previously-passing test "deleted" for a
  parameterized test still present.
- **Reproduction**: pytest named a parameter `text6` (auto id) in one version vs
  full text in another.
- **Classification**: brittle comparison.
- **Root cause**: exact node-id comparison across pytest versions / escaping.
- **Fix**: `_norm_id` normalises escapes; bridge same-base/same-count auto ids;
  give fragile parametrizations explicit `ids=`.
- **Invariant gap**: REQ-INV-001 (record/idempotency) is unaffected; this protected
  the regression signal (G5).
