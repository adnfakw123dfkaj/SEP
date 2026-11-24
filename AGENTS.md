# AGENTS.md — coding-agent governance entry point

This is the single entry point the coding agent reads before touching the
repository. **Read in this order, then plan, then wait for human approval before
writing code.**

## 1. Build target

The application is `tradingagents/` (Python package `tradingagents` + `cli`).
Source lives there; tests are `tradingagents/tests`, exposed as **offline**
(`test/offline`) and **live** (`test/live`) via markers. Install/run from
`tradingagents/`.

## 2. Reading order (architecture artifacts)

1. `architecture-blueprint.md` (master constraints)
2. `docs/architecture/adr/` (decisions: `001-part5-security-rating-boundaries.md`,
   `002-multi-agent-langgraph-authority.md`)
3. `docs/architecture/invariants.md` and `trace-matrix.md`
4. `docs/architecture/memory-design.md`, `permission-model.md`,
   `runtime-policy-catalog.md`, `evaluation-table.md`
5. `docs/req/requirements.yaml` (machine-readable requirements + fit criteria)
6. `docs/code-governance/` (structural-constraints, verification-constraints,
   mcp-tool-manifest)
7. `docs/gate-intro.md` (G1–G7 rules) and `.opencode/rules.md`, `.agent/rules.md`

## 3. Code baseline

Extend the existing structure; do not replace modules. Module↔element mapping and
"one element per module" are in `docs/code-governance/structural-constraints.md`.
Public functions state the `REQ-*`/`REQ-INV-*` (and ADR) they implement.

## 4. Readable / modifiable / frozen

- **Readable**: whole repository.
- **Modifiable (with review)**: application code, tests, docs.
- **Frozen unless approved + ADR + human review**: safety-relevant paths —
  `tradingagents/{agents,memory,dataflows,security,contracts,graph}/`,
  `scripts/gates/`, `.github/workflows/`, `docs/req/req-schema.json`,
  `docs/approvals/**`. See `.opencode/permissions.jsonc`.

## 5. Module organization & integration contracts

Contracts cross module boundaries via `tradingagents/contracts/` (typed models).
The **composition root** `graph/trading_graph.py` is the single writer of
authoritative state (run state, report, manifest, memory, rating). Agents are
advisory only. See structural-constraints §4.

## 6. Verification requirements the generated code must satisfy

- `ruff check` and `pyright` clean (`pyrightconfig.json` scope).
- `pytest tests -q` (offline) green; no regressions vs
  `docs/req/regression-baseline.json`.
- Gates G1–G7 must pass (see `docs/gate-intro.md`): test approval, static
  analysis, schema, semantic eval, regression, AI-use log, ownership.
- Every fit criterion has a test; invariants have a failing-when-violated test
  (`docs/code-governance/verification-constraints.md`).

## 7. Workflow

Produce an execution plan (traceability, interface contract, scope, tests,
steps) and **stop for human approval before generating code**, then proceed with
human gates at each stage (see `Prompt.md`).
