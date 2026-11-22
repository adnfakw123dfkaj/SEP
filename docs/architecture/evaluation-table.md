# Candidate Evaluation Table

Comparison of architectural candidates that justifies the chosen architecture
(ADR-001). Scored against the architectural drivers in
`architecture-blueprint.md` §2.

| Criterion | A: Multi-agent LangGraph (chosen) | B: Single monolithic agent | C: Multi-process agents | D: Deterministic rule engine |
|---|---|---|---|---|
| Auditable per-claim evidence (D4) | Strong — per-node reports + evidence refs | Weak — one opaque transcript | Strong | N/A (no prose) |
| Deterministic authority (D2) | Strong — separate commit gate | Weak — model output is the result | Strong | Strong |
| Point-in-time (D1) | Strong — data layer clamps dates | Strong (same data layer) | Strong | Strong |
| Safety (D3) | Strong — guards between nodes | Weak — fewer boundaries | Strong | Strong |
| Latency/cost control (D5) | Good — role-tiered models, budget guard | Poor — one unbounded call | Poor — IPC overhead | Excellent (cheap) |
| Multi-perspective synthesis | Strong — bull/bear + risk debates | Weak | Strong | None |
| Testability | Strong — per-node unit tests | Weak | Medium | Strong |
| Implementation cost | Medium | Low | High | Medium |

Decision: **A** balances auditable multi-perspective analysis, deterministic
authority, and bounded cost. B cannot be audited or bounded; C adds orchestration
cost with no benefit (agents share one state and are LLM-latency-bound); D cannot
perform the required synthesis.

See `option-ledger.md` for rejected options and when to reconsider them.
