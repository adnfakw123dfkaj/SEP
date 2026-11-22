# ADR-002 — Multi-agent LangGraph pipeline with deterministic authority

- Status: Accepted
- Date: 2026-11-22
- Supersedes: none (see ADR-001 for the Part 5 detail decision)

## Context

The system must analyse an instrument on a date and produce a defensible,
auditable rating. Requirements demand: point-in-time data, deterministic rating
authority, untrusted-input safety, auditable records, bounded latency/cost, and
structured debate (see `architecture-blueprint.md` §2). The analysis is inherently
multi-perspective (technical, fundamental, news, sentiment, bull/bear, risk).

## Decision

Use **LangGraph** as the orchestration substrate, modelling each role as a graph
node over a shared typed state, with the following shape:

- Analysts fan out from `START` (parallel, in-process asyncio) and join before the
  research debate.
- Bull⇄Bear and the three-way risk debate are **sequential, bounded** turns via
  conditional edges (complete path maps).
- A **composition root** (`graph/trading_graph.py`) is the only place that writes
  the final rating and the run record.

### AI layered context structure (every model turn receives)

1. **Identity** — resolved instrument context (`agents/context.py`), so the model
   cannot substitute a different company/ticker.
2. **Standing constraints** — role instruction + output-language + "report what
   tools support" (no `NO_EXTERNAL_TOOLS` where tools are bound).
3. **Retrieved knowledge** — tool results (market snapshot, fundamentals, news,
   social blocks) and, for the Portfolio Manager, `past_context` lessons.
4. **Conversation / debate history** — analyst/tool message history within the
   analyst subgraph; debate history for researchers/debators.
5. **Resumable state** — LangGraph checkpoint (opt-in via `--checkpoint`).
6. **Current task** — the specific node's instruction (e.g. "critique the bull
   case").

### Assembly pipeline

`context.py` fragments → per-node prompt template → (optional structured-output
binding) → provider call. Deduplicate: same-role fragments are injected once.
Prioritise: identity and standing constraints always first. Budget: per-profile
input trimming (tool-output and report-injection character caps) and `max_tokens`.

### Token-budget cap and compaction threshold

Per-profile hard caps: Quick 25k, Standard 60k, Deep 150k; soft targets 20k/50k/
120k. The runtime enforces the **hard cap before each call** (`GuardedLLM`), and
trims injected input by character budget. Compaction (summarise / cheaper-model)
is implemented in `cost/` and used by the audit facade but **not wired into the
runtime path** (the runtime stops hard, to `REVIEW`, rather than degrade).

### Re-injection of critical constraints after compaction

Protected evidence (verified snapshot, evidence refs, risk constraints) is never
summarised away: `summarize_context(protected_keys=...)` keeps those keys verbatim
where compaction is used. At runtime, identity (Identity) and standing
constraints are part of every prompt and are never subject to the trimming that
applies only to tool/report bodies.

## Alternatives considered

- **Single large agent** — rejected: not auditable, cannot bound cost per role,
  no independent perspectives.
- **Multiple processes per agent** — rejected: agents share one graph state and
  are latency-bound on the LLM; a process boundary adds orchestration cost with
  no benefit (parallelism within one process is enough for the independent
  analysts).
- **Deterministic rule engine only** — rejected: cannot do news/fundamental
  synthesis; the requirement explicitly wants an AI component.

## Consequences

- Pros: modular, testable per node, bounded debates, a single authoritative write
  path, budgetable.
- Cons: LLM output is non-deterministic (mitigated by deterministic rating
  authority and `REVIEW`); the debate chain is inherently serial (cannot be
  parallelised further).

## Conditions that reopen the decision

- If debate latency dominates and the workload can be split into independent
  shards with a merge step.
- If a stable, deterministic analysis suffices for a task variant.
- If cost routing must become runtime (then wire `cost/router.py` into the graph).
