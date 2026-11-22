# .opencode/rules.md — always-on behavioral rules (human-only)

Human-only file. The coding agent follows these on every turn. Editing this file
requires a human owner (see `.opencode/permissions.jsonc` GR-4).

1. **Plan before code.** Start by producing an execution plan (traceability to
   `REQ-*`, interface contract, scope boundaries, testing strategy, steps) and
   stop for human approval before writing any code (`Prompt.md`).
2. **Read the constraints first.** `AGENTS.md` → `architecture-blueprint.md` →
   ADR → invariants/trace → requirements → code-governance.
3. **Never fabricate.** If a tool/credential/data source is unavailable, report it
   as unavailable; do not estimate or invent values (REQ-SEC-001, point-in-time).
4. **Extend, don't replace.** New work extends the baseline; removing/replacing an
   element needs an ADR + human approval (structural-constraints).
5. **Stay in scope.** Touch only modules you are working on; cross-module data
   goes through `contracts/`.
6. **Respect authority boundaries.** Agents are advisory; only the composition
   root writes authoritative state; guards block, they don't decide.
7. **Protect secrets.** Never read/write `.env`/keys; secrets come from env only.
8. **Every change is verified.** Add/keep tests; each fit criterion has a test;
   each invariant has a failing-when-violated test; no regressions.
9. **Declare provenance.** Public functions cite the `REQ-*`/`REQ-INV-*` (and ADR)
   they implement.
10. **Satisfy the gates.** A code/prompt change updates `docs/ai-use-log.yaml`
    (G6); safety-path changes need an approval (G1) and review; run the offline
    suite and `ruff`/`pyright` before proposing a merge.
11. **No self-approval.** The agent may not create/modify `docs/approvals/**`;
    that is a human action.
12. **Stop at human gates.** Requirements/architecture changes, plan approval,
    and merge are human decisions recorded in the session.
