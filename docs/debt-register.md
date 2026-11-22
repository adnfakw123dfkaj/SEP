# Technical Debt Register

AI-era debt categories. Each item: what, category, impact, trigger to repay.

| ID | Item | Category | Impact | Repay trigger |
|---|---|---|---|---|
| DEBT-01 | Runtime over-budget does **hard-stop to REVIEW**; the summarize / cheaper-model / approval routing (`cost/router.py`, `summarize_context`, `select_cheaper_model`, `apply_quality_floor`) is implemented+tested but **not wired** into the graph. | guardrail debt | Over-budget runs are wasted instead of degraded. | When overruns are frequent, or a runtime quality floor can be enforced end-to-end. |
| DEBT-02 | Price table lacks `deepseek-v4-flash` while `.env` uses it (`deepseek-v4-flash`/`deepseek-v4-pro`); only `deepseek-flash`/`deepseek-v4-pro` are priced. | hidden dependency | A real run with the `.env` model fails the cost monitor. | Before any live cost run; reconcile model IDs or extend the price table. |
| DEBT-03 | Several `tests/req/*` live/integration tests are `require()`-skip stubs rather than real assertions (debate live metrics, latency p95). | evaluation debt | "Green" may mean "skipped", not "verified". | Replace with real owner-run integration or recorded fixtures. |
| DEBT-04 | Requirement `status: partial` on several entries (e.g. REQ-FR-004 evidence/manifest wiring historically partial; REQ-COST-001 routing). | evaluation debt | Registry may over/under-state completion. | Re-audit each partial before final acceptance. |
| DEBT-05 | Token estimator is an approximation, not a provider tokenizer; cost error can approach the 5% threshold. | evaluation debt | Pre-call estimate may mispredict. | If pre-call gating must be exact, use provider usage or a tokenizer. |
| DEBT-06 | D8 uses root `src/README.md` plus root `test/{offline,live}` wrappers; source and tests remain in `tradingagents/`, not a physical `src/`+`test` tree. | agent-induced bloat (structure) | Layout satisfies a reviewable root entry point but differs from a literal D8 tree. | If the course requires literal source/test trees, do a physical migration with import, packaging, test, and CI updates. |
| DEBT-07 | Gate rules are duplicated conceptually between docs (`gate-intro`, `gates-deployment`) and code; drift risk. | hidden dependency | Documentation may diverge from gate behaviour. | On any gate change, reconcile docs+code in one PR. |
| DEBT-08 | Prompt text is inline in code (no `prompts/` versioned files yet). | prompt rot | Harder to review/version prompts. | When prompts are consolidated to `prompts/prompt_vX.Y.yaml` (D9). |
| DEBT-09 | Gate-level branch protection cannot be enforced on a private personal repo (platform limit). | guardrail debt | Gates run but do not physically block merges. | If repo goes Public or org Team is used. |

Owners and dates are tracked in the PR that introduces or repays each item.
