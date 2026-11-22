# Prompt.md — static startup prompt (D9)

This is the single static prompt the coding agent reads after `AGENTS.md`. It is
the launch instruction: it starts a **supervised** session, not an unattended
run-to-completion. Do not skip the human gates.

## Instruction to the agent

You are working on TradingAgents under human supervision. Begin by reading, in
order: `AGENTS.md`, `architecture-blueprint.md`, the ADRs under
`docs/architecture/adr/`, `docs/architecture/invariants.md` and `trace-matrix.md`,
`docs/req/requirements.yaml`, and `docs/code-governance/`.

Then produce an **execution plan** and STOP for human approval before writing any
code. The plan must contain:

1. **Traceability** — the `REQ-*` / `REQ-INV-*` this work implements, and their
   fit criteria (metric + threshold + verification).
2. **Interface contract** — modules touched and any `contracts/` change.
3. **Scope boundaries** — what is in and out; confirmed no safety-critical path
   is touched without an ADR.
4. **Testing strategy** — the tests to add/keep, including at least one negative
   test, and how regressions are avoided.
5. **Steps** — the ordered implementation steps and the evidence each produces.

## Human gates (do not bypass)

- Requirements/architecture changes, and the plan itself, require human approval.
- After approval, implement in small steps; after each step, run the checks
  (ruff, pyright, offline `pytest`, gate self-tests) and report.
- Before proposing a merge: update `docs/ai-use-log.yaml` (G6), ensure an approval
  exists for safety-path/test changes (G1), and confirm G1–G7 pass.
- Never self-approve (`docs/approvals/**`); never merge; never run live/integration
  tests unattended — those are the human owner's actions.

## Operating rules

Follow `.opencode/rules.md` and `.agent/rules.md` on every turn. If a tool,
credential, or data source is unavailable, report it as unavailable; never
fabricate values.
