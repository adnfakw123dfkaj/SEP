# Structural Constraints

Module organization rules the coding agent and reviewers enforce. These bind how
the codebase is shaped; they do not specify behaviour.

## 1. One architectural element = one module

Each element in `architecture-blueprint.md` §4 maps to exactly one package/module:

| Element | Module |
|---|---|
| Orchestration | `tradingagents/graph/` |
| Agents (analysts/researchers/managers/trader/risk) | `tradingagents/agents/` (+ `agents/debate/`) |
| Data routing & vendors | `tradingagents/dataflows/` (+ `vendors/`) |
| LLM providers | `tradingagents/llm_clients/` |
| Memory | `tradingagents/memory/` |
| Contracts | `tradingagents/contracts/` |
| Cost / latency | `tradingagents/cost/` |
| Evidence | `tradingagents/evidence/` |
| Records | `tradingagents/records/` |
| Security | `tradingagents/security/` |
| CLI | `cli/` |
| Gate tooling | `scripts/gates/` |

A new element is a new module; do not stuff a second element into an existing one.

## 2. Extend, never replace

New work **extends** the existing baseline (add a node, a vendor, a tool, a
contract field) — it does not rewrite or drop existing elements. Removing or
replacing an element requires an architecture decision (ADR) and human approval.

## 3. Every module/function references its decision and invariant

Public functions and every module that enforces a rule or a contract state, in its
docstring, the `REQ-*` / `REQ-INV-*` (and, where relevant, the ADR) it implements.
Examples already in the tree: `records/atomic.py` (REQ-INV-001),
`security/tool_guard.py` (REQ-SEC-001), `cost/budget.py` (REQ-COST-001),
`evidence/fidelity.py` (REQ-QUAL-002). The trace matrix
(`docs/architecture/trace-matrix.md`) is the authoritative map.

## 4. Authority boundaries

- Agents are **advisory**: they produce text, never persist state or the rating.
- The **composition root** (`graph/trading_graph.py`) is the only writer of the
  run state, report, manifest, memory log and rating record.
- **Guards** (`security/`, `cost/guard.py`, `rating_authority.py`) block/deny; they
  do not decide the trade.

No module may bypass the composition root to write authoritative state, and no
agent may call a tool outside its role's allowlist (see `mcp-tool-manifest.md`).

## 5. Integration contracts

Cross-module data crosses through `tradingagents/contracts/` (typed models), not via
copied internal logic. Changing a contract is a PR + owner approval + updated
contract tests.
