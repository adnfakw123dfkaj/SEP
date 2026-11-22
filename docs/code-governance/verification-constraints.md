# Verification Constraints

The rules the verification agent applies and every contributor follows. Concrete
commands run from `tradingagents/` unless noted.

## 1. Every fit criterion has at least one test

Each `REQ-*` in `docs/req/requirements.yaml` carries one or more `fit_criterion`
entries; each names a `verification` command. That command must exist and pass.
The authoritative mapping is `docs/architecture/trace-matrix.md`. A requirement
with no runnable verification is not "done" (see `status: partial` entries).

## 2. Every invariant has a test that fails when it is violated

The zero-tolerance invariants (REQ-INV-001..004) each have a negative test that
would fail if the invariant were broken:

- REQ-INV-001 — `tests/req/test_records.py::test_idempotent_append`,
  `::test_fault_injection` (a partial/duplicate record must fail).
- REQ-INV-002 — `tests/req/test_point_in_time.py` (a future-dated item must not
  appear).
- REQ-INV-003 — `tests/req/test_rating_invariant.py::test_adversarial_text`,
  `::test_fuzz` (an out-of-set or overridden rating must fail).
- REQ-INV-004 — `tests/security/test_secret_redaction.py` (a leaked secret must
  fail).

## 3. Every test references the requirement or invariant it verifies

Each test file/docstring cites the `REQ-*` / `REQ-INV-*` it verifies (the `tests/req`
and `tests/security` files do this in their module docstring and per-test
docstrings). A test with no trace is not accepted.

## 4. Every round runs all prior suites — zero regressions

Each new round of work runs the **full** prior suite; any regression blocks the
merge. The baseline of previously-passing tests is
`docs/req/regression-baseline.json`; the gate `scripts/gates/check_regression.py`
compares against it. Deleting a previously-passing test requires a deletion
approval (`docs/approvals`).

## 5. Three-tier verification

1. **Structural** — imports resolve, module boundaries hold, permissions hold,
   architectural fitness functions pass:
   - `python -m ruff check .` (lint)
   - `pyright` (progressive type check; see `pyrightconfig.json`)
   - `python scripts/gates/run_static_checks.py` (contract/security/api_surface/
     permission)
2. **Regression** — all prior suites pass:
   - `python -m pytest tests -q` (offline; see `test/offline/`)
3. **Behavioural** — quality/faithfulness/safety thresholds and zero safety
   escapes:
   - `pytest tests/req/test_report_faithfulness.py` (faithfulness/citations)
   - `pytest tests/req/test_debate_quality.py` (debate quality)
   - `pytest tests/req/test_rating_invariant.py` (rating authority)
   - live end-to-end (integration): `pytest tests -m integration` (owner-run)

## 6. CI blocking gates

The gates in `.github/workflows/gates.yml` (G1–G7) and `.github/workflows/ci.yml`
enforce: test approval (G1), static analysis (G2), schema (G3), semantic eval (G4),
regression (G5), AI-use log (G6), ownership (G7), plus the application test/lint/
smoke jobs. See `docs/gate-intro.md` and `docs/code-governance/gates-deployment.md`.
