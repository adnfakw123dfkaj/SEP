# Risk List

Assumptions that could become defects, with review triggers.

| Risk | Impact | Review trigger / guard |
|---|---|---|
| LLM non-determinism makes ratings differ run-to-run | Reproducibility concerns | Deterministic rating authority + `REVIEW`; documented in README. Re-review if reviewers expect identical outputs. |
| Vendors change schemas/rate limits (Yahoo, SEC, FRED, Reddit 403) | Missing data, degraded reports | Typed errors + sentinels + fallback chain; monitor `DATA_UNAVAILABLE`. Re-check on repeated vendor failures. |
| Point-in-time gaps (live-only social/news on historical runs) | Look-ahead leakage | `withhold_*` + `<unavailable>` markers; tests in `test_point_in_time.py`. Re-review when adding a new data source. |
| Cost router implemented but not wired | Over-budget runs hard-stop (REVIEW) instead of degrading | Documented in REQ-COST-001; wire `cost/router.py` before claiming graceful degradation. |
| Token estimator is approximate (not a provider tokenizer) | Cost estimate error near the 5% threshold | Price table + provider usage is source of truth; estimate only for pre-call warning. |
| Gate infra changes can be bypassed if rules diverge per branch | Gate integrity | Rules live only on master; `docs/gate-intro.md`. Re-review any change to `scripts/gates/` / `gates.yml`. |
| Root `src/` and `test/{offline,live}` are compatibility entries; source and tests still live under `tradingagents/` | D8 may still be judged as a non-physical layout | Documented in root `README.md`, `src/README.md`, and root `test/*/README.md`. Reconcile with a physical migration if the course requires literal source/test trees. |
| Secrets in `.env` | Leakage | `.env` git-ignored; `api_key_env` reads env; redaction + secret scan. Re-check before any release. |
