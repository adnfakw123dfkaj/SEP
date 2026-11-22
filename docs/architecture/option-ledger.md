# Option Ledger

Rejected architectural options and when they should be reconsidered.

| Option | Why rejected now | Reconsider when |
|---|---|---|
| Multi-process agents (one OS process per role) | Agents share one graph state and are LLM-latency-bound; a process boundary adds orchestration/serialization cost with no throughput gain. Parallelism inside one process (analysts) already covers the independent work. | A role needs CPU-heavy local compute, or isolation/fault-domains become a hard requirement. |
| Runtime cost routing (summarise → cheaper model → approval) wired into the graph | Implemented in `cost/` but currently the runtime hard-stops to `REVIEW` over hard budget instead of degrading; wiring needs protected-evidence guarantees across all nodes. | Budget overruns become frequent in practice, or a quality floor can be enforced end-to-end at runtime. |
| Full vector RAG knowledge base for glossary/company facts | Out of current scope; adds heavy deps (embeddings/vector store) and a maintenance surface. | A maintainable, updatable knowledge/QA surface becomes a course requirement. |
| Event-sourced (append-only events) run history | Heavier than the current manifest + memory log for the course scope. | Full replay/audit with corrections becomes required. |
| Hashing-chain tamper-evident audit | Engineering cost high; current atomic+idempotent records suffice. | Regulatory-style tamper evidence is required. |

No option here is a "never"; each has an explicit trigger above.
