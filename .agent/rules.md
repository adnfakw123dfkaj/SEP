# .agent/rules.md — project covenant

Binding rules for everyone (human and agent) working on this repository.

## Abstraction limits

- Keep each module at one level of abstraction matching its element
  (`docs/code-governance/structural-constraints.md`). Do not leak vendor/provider
  details up into agents, or agent reasoning down into the data layer.
- Cross-module contracts are typed models in `tradingagents/contracts/`.

## Dependency constraints

- No new third-party dependency without review; the core stays on the pinned set
  in `tradingagents/pyproject.toml`.
- The data layer talks to vendors only through `dataflows/router.py`; models only
  through `llm_clients/`. No agent imports a vendor SDK directly.
- Optional capabilities (Bedrock, RAG, etc.) are isolated behind extras/flags.

## Test independence (at least one negative test per feature)

- Every feature has at least one **negative** test (a case that must fail or be
  rejected), in addition to the happy path.
- Tests are independent: no ordering dependence; `tests/conftest.py` isolates
  config, caches, network.

## Safety-critical changes

Changing safety-critical code — `tradingagents/{agents,memory,dataflows,security,
contracts,graph}/`, `scripts/gates/` — requires:
1. an **architecture decision record** (ADR) capturing the decision, and
2. **human approval** recorded in `docs/approvals/`.

This is enforced by the gates (G1 test approval, G2 permission) and branch
protection.

## Context freshness

Rules and governance artifacts are updated **within one sprint of a requirements
change**. When `docs/req/requirements.yaml` changes, the affected
`docs/architecture/` artifacts, `trace-matrix.md`, and this covenant are revisited
in the same or next sprint, and the change is logged.

## Evidence

Every merge carries: test output, the fit-criterion evidence, and an AI-use-log
entry (G6). Decisions and their rationale live in ADRs and the memory log.
