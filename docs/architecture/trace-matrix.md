# Trace Matrix

Every requirement mapped to its enforcing component, its test/evidence, and its
runtime monitor.

| Requirement | Enforcing component | Test / evidence | Runtime monitor |
|---|---|---|---|
| REQ-FR-001 Run profiles | `profiles.py`, `graph/setup.py`, `graph/analyst_execution.py`, `default_config.py` | `tests/req/test_profiles.py` | `RunManifest.profile`, `run_settings()` |
| REQ-FR-002 Preflight ticker/data | `preflight.py`, `dataflows/symbols.py` | `tests/req/test_preflight.py`, `tests/req/test_preflight_live.py` (live) | preflight result in manifest / CLI error |
| REQ-FR-003 Structured debate | `agents/debate/` (schemas, validator, convergence), researchers adapters, `graph/conditional_logic.py` | `tests/req/test_debate_protocol.py` | debate transcript, `max_rounds` |
| REQ-QUAL-001 Debate quality | `agents/debate/quality.py` | `tests/req/test_debate_quality.py` | quality metrics in report |
| REQ-FR-004 Evidence + manifest | `contracts/{evidence,manifest}.py`, `evidence/registry.py`, manifest writer, `reporting.py` | `tests/req/test_evidence_manifest.py`, `tests/req/test_claims.py` | `RunManifest`, evidence index in report tree |
| REQ-QUAL-002 Report fidelity | `evidence/fidelity.py` | `tests/req/test_report_faithfulness.py` | contradiction/citation metrics |
| REQ-INV-001 Atomic/idempotent records | `records/atomic.py`, `records/idempotency.py`, `memory/log.py` | `tests/req/test_records.py` | record hash, index |
| REQ-FR-005 Cache/checkpoint/degrade | `cache/`, `graph/checkpointer.py`, `resilience.py` | `tests/req/test_checkpoint_resume.py`, `test_cache.py`, `test_fallback.py` | `fallback_events`, cache hits |
| REQ-INV-002 Point-in-time | `dataflows/date_window.py`, vendor `withhold_*`, `memory.get_past_context(as_of)` | `tests/req/test_point_in_time.py` | as-of dates in manifest |
| REQ-INV-003 Deterministic rating | `agents/rating.py`, `rating_authority.py`, commit gate in `graph/trading_graph.py` | `tests/req/test_rating_invariant.py` | committed rating + reason codes |
| REQ-SEC-001 Input/output safety | `security/{sanitize,validate_output,tool_guard,tool_node}.py` | `tests/security/test_prompt_injection.py` | `security_events` in manifest |
| REQ-INV-004 No secret leak | `security/redaction.py`, `dataflows/net.py`, `llm_clients/api_key_env.py` | `tests/security/test_secret_redaction.py` | secret-scan CI gate; redaction log |
| REQ-PER-001 Tiered latency | profiles, cache/checkpoint, early-stop, model tiers, `scripts/bench_latency.py` | `tests/req/test_latency.py` (live), `scripts/bench_latency.py` | bench p95/p99 report |
| REQ-COST-001 Token budget + report | `cost/`, `graph/trading_graph` GuardedLLM, `profiles.py`, `scripts/token_audit.py` | `tests/req/test_token_cost.py` | `CostReport`, hard-stop `budget_exceeded` |

Gate obligations (process-level, see `docs/gate-intro.md`): G1 test approval,
G2 static analysis, G3 schema, G4 semantic eval, G5 regression, G6 AI-use log,
G7 ownership — enforced in `.github/workflows/gates.yml`.
