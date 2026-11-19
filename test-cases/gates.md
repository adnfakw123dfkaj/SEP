# Blocking Gates — Test-Case Specification

Conformance and strategy test cases for the six blocking gates (PDF §6, D7) and
branch protection, as they will be deployed on GitHub for this repository.

This is a **specification** (markdown, no runnable code yet), consistent in style
with `test-cases/part1..6`. It covers the *gate layer* — different from the 14
product requirements in `requirements-final.md`. Where that document dropped the
gates as "too heavy", the course PDF mandates them; this file treats the gates as
required.

---

## 0. Deployment model (read this first — it constrains every case)

The gates are **one set of rules, owned only by `master`**, run at **two layers**.
This model is what the cases below assert.

| Layer | Trigger | Rules used | Code checked | On failure |
|---|---|---|---|---|
| **Layer 1 — branch self-check** | push to any feature branch, or manual | **master's** gate rules (via reusable workflow) | that branch's code | warn only, never blocks |
| **Layer 2 — PR blocking check** | `pull_request` targeting `master` | **master's** gate rules (`ci.yml` on master) | the PR head branch's code | **blocks merge** (required status check) |

**Single source of truth.** Gate logic lives only on `master`:

```
.github/workflows/gates.yml        # reusable workflow (workflow_call) — the rules
.github/workflows/ci.yml           # layer-2 entry: calls gates.yml on pull_request → master
scripts/gates/check_*.py           # the decision logic for each gate (testable)
```

A feature branch carries **no gate logic of its own**. It carries only a thin
stub (or nothing) — see TC-G7-STRAT-03 — and the workflow that runs on its push
`uses` the `master` reusable workflow, so it always evaluates **the latest master
rules**, never a stale snapshot copied when the branch was cut.

**Branch isolation.** Every run — layer-1 self-check and layer-2 PR check — runs
on its own fresh GitHub runner, checks out only its own ref, and writes only its
own artifacts. No state, cache, or artifact is shared across branches. Parallel
branches cannot see or affect each other's verification scope.

**Anti-bypass (critical on GitHub).** On a `pull_request` event GitHub runs the
workflow file from the **base branch (`master`)**, but checks out the **head
branch's** code. The gate scripts must **also** be taken from `master`, never from
the PR head, or a PR could edit `check_*.py` to always pass. The layer-2 workflow
therefore checks out `master` for `scripts/gates/` and the PR head only for the
code under test. (See TC-G7-STRAT-05.)

**Trunk branch** is `master` (the repository's current default). All references
below are to `master`; if the default is ever renamed to `main`, substitute the
name everywhere in the workflows.

**Where gate logic lives.** Decision logic is in **testable Python scripts**
(`scripts/gates/check_*.py`), invoked by the YAML. The YAML only does orchestration
(checkout, install, feed PR context as JSON/env, run script, gate on exit code).
This is what lets each gate's pass/block behaviour be verified offline by pytest
(see §2) as well as live on GitHub (see §3).

---

## 1. Gate model and ID scheme

Gate IDs: `G1`..`G6` for the six gates, `STRAT` for the deployment-strategy rules
above, `BP` for branch protection, `SELFTEST` for layer-1/layer-2 duality.

Case ID: `TC-G<n>-<short>-<nn>`. Kind (same legend as `test-cases/README.md`):

| Kind | Meaning | How verified |
|---|---|---|
| **OFFLINE** | gate decision script run against synthetic inputs; asserts block/pass | pytest, no network, no GitHub |
| **GITHUB** | true end-to-end on GitHub (PR/branch events, branch protection) | a real PR dry-run or `act`; marked integration |
| **CONFIG** | inspects the workflow/branch-protection configuration itself | a config-parse test |

Each case: **Given / When / Then / Pass criterion / Evidence / Traces to** (gate
clause).

---

## 2. The six gates

### Gate 1 — Test approval gate

> No code change merges unless the tests for the change were approved **before
> implementation began**.

**Approval evidence (decided here, must be built):** a committed, timestamped
approval record at `docs/approvals/<pr-or-change-id>.yaml` with fields
`change_id`, `tests` (paths), `approved_by`, `approved_at` (ISO-8601). The gate
asserts the approval exists, covers the test files that the PR adds/changes, and
`approved_at` is **earlier than the first implementation commit** touching
non-test code.

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-G1-APPROVAL-01 | OFFLINE | Approved-before-implementation passes | no violation |
| TC-G1-APPROVAL-02 | OFFLINE | Missing approval on code change blocks (negative) | blocked |
| TC-G1-APPROVAL-03 | OFFLINE | Approval after implementation blocks (negative) | blocked |
| TC-G1-APPROVAL-04 | OFFLINE | Approval not covering changed tests blocks (negative) | blocked |
| TC-G1-APPROVAL-05 | OFFLINE | Tests-only PR needs no approval | passes |
| TC-G1-APPROVAL-06 | GITHUB | A real PR without approval cannot merge | merge blocked |

- **TC-G1-APPROVAL-01** — Given an approval whose `approved_at` precedes the first
  code commit and lists the changed test paths. When the gate runs. Then no
  violation. *Evidence:* gate JSON report with `violations: []`.
- **TC-G1-APPROVAL-02** — Given a code change with no approval file. When the
  gate runs. Then blocked, reason `missing approval`. (mandatory must-fail)
- **TC-G1-APPROVAL-03** — Given an approval timestamped after the first code
  commit. Then blocked, reason `approval after implementation`. (must-fail)
- **TC-G1-APPROVAL-04** — Given an approval listing a different test file than the
  one changed. Then blocked, reason `approval does not cover changed tests`.
- **TC-G1-APPROVAL-05** — Given a PR that only adds/changes tests, no production
  code. Then it passes without an approval (tests are the thing being approved).
- **TC-G1-APPROVAL-06** — GITHUB: raise a real PR committing code with no approval;
  the required check fails and merge is disabled; the failure message names the
  gate and reason.

### Gate 2 — Static analysis gates

> Lint, type-checking, dependency checks on **every commit**; contract, security,
> API-surface, permission checks on any PR touching **safety-relevant paths**.

**Safety-relevant paths (decided here):** `tradingagents/agents/`,
`tradingagents/memory/`, `tradingagents/dataflows/`, `tradingagents/security/`,
`tradingagents/contracts/`, `tradingagents/graph/`, `scripts/gates/`.

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-G2-STATIC-01 | OFFLINE | Lint failure blocks | blocked |
| TC-G2-STATIC-02 | OFFLINE | Type-check failure blocks | blocked |
| TC-G2-STATIC-03 | OFFLINE | Dependency check failure blocks | blocked |
| TC-G2-STATIC-04 | OFFLINE | Safety-path PR triggers contract/security/API/permission checks | checks run |
| TC-G2-STATIC-05 | OFFLINE | Non-safety PR skips the heavy checks | not run |
| TC-G2-STATIC-06 | CONFIG | Workflow wires lint+type+dep on every commit | present |
| TC-G2-STATIC-07 | GITHUB | Safety-path PR with a contract violation blocks | merge blocked |

- **TC-G2-STATIC-01..03** — Given a tree with a lint / type / dependency error.
  When the gate runs each tool. Then it blocks with the tool's exit code and the
  offending file/line. (must-fail each)
- **TC-G2-STATIC-04** — Given a diff touching `tradingagents/agents/…`. When the
  gate classifies paths. Then it runs the contract, security, API-surface and
  permission checks in addition to lint/type/dep.
- **TC-G2-STATIC-05** — Given a diff touching only `README.md`. Then only
  lint/type/dep run; the safety-path checks are skipped and recorded as skipped.
- **TC-G2-STATIC-06** — CONFIG: parse `ci.yml`; assert lint, type-check
  (pyright, progressive via `pyrightconfig.json`), dependency-audit (pip-audit) are wired to run on
  every push/PR, and that the safety-path condition gates the heavier checks.
- **TC-G2-STATIC-07** — GITHUB: a PR touching a safety path that removes a
  contract field; the contract check blocks the merge.

### Gate 3 — Schema gate

> The requirements registry validates against its JSON schema.

**Artifact (must be built):** `docs/req/requirements.yaml` (the 14 entries) +
`docs/req/req-schema.json` (JSON Schema requiring `id`, `type`, `priority`,
`statement`, `fit_criterion{metric,threshold,verification}`; `priority` ∈
Must/Should/Could/Won't; `type` ∈ the Appendix-M set).

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-G3-SCHEMA-01 | OFFLINE | Valid registry passes | valid |
| TC-G3-SCHEMA-02 | OFFLINE | Entry missing a fit-criterion field fails (negative) | invalid |
| TC-G3-SCHEMA-03 | OFFLINE | Priority out of MoSCoW set fails (negative) | invalid |
| TC-G3-SCHEMA-04 | OFFLINE | Duplicate ID fails (negative) | invalid |
| TC-G3-SCHEMA-05 | CONFIG | Schema gate runs on any change to `docs/req/**` | wired |
| TC-G3-SCHEMA-06 | GITHUB | PR breaking the registry blocks | merge blocked |

- **TC-G3-SCHEMA-01** — Given the committed registry + schema. When validated.
  Then every entry conforms; exit 0; report lists 14 entries validated.
- **TC-G3-SCHEMA-02..04** — (must-fail each) an entry missing `threshold`, a
  `priority: High` (not MoSCoW), and a duplicated `id` each fail with the
  offending entry id and field named.
- **TC-G3-SCHEMA-05** — CONFIG: parse `ci.yml`; the schema validation runs
  whenever `docs/req/**` changes (and as part of the always-on set).
- **TC-G3-SCHEMA-06** — GITHUB: a PR adding a malformed requirement entry is
  blocked and the report points at the bad entry.

### Gate 4 — Semantic evaluation gate

> For any **prompt or model change**, replay a fixed evaluation set against
> quality thresholds before reaching production; a failed threshold blocks and is
> reported.

**Change-detection rule (decided here):** a PR "touches prompts/models" if it
changes `prompts/**`, any `*_analyst.py` / `prompts.py` under `agents/`, the model
config keys (`deep_think_llm`, `quick_think_llm`, providers, `temperature`,
thinking knobs), or `prompts/` versioned files. Non-matching PRs skip the eval.

**Fixed eval set (must be built):** `eval/fixed_set.jsonl` (recorded inputs +
expected-shape) + `eval/harness.py` (offline, deterministic, threshold-scored —
the quality floor reuses the metrics from `TC-P2-QUAL001` / `TC-P3-QUAL002`).

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-G4-EVAL-01 | OFFLINE | Prompt change is detected | classified as eval-relevant |
| TC-G4-EVAL-02 | OFFLINE | Model change is detected | classified as eval-relevant |
| TC-G4-EVAL-03 | OFFLINE | Non-eval change skips cleanly | skipped, not failed |
| TC-G4-EVAL-04 | OFFLINE | All thresholds pass → gate passes | pass |
| TC-G4-EVAL-05 | OFFLINE | One threshold below → gate blocks + reports (negative) | blocked + report |
| TC-G4-EVAL-06 | GITHUB | Prompt-change PR below threshold blocks | merge blocked |

- **TC-G4-EVAL-01/02** — Given a diff of each kind. When the classifier runs.
  Then `eval_relevant == true`.
- **TC-G4-EVAL-03** — Given a docs-only diff. Then `eval_relevant == false`;
  the eval job is skipped; the gate records "skipped". (boundary, avoids wasting
  runs)
- **TC-G4-EVAL-04** — Given the fixed set and a passing model. When the harness
  replays it. Then every threshold (faithfulness, relevance, REVIEW-rate,
  numeric-consistency) is met; exit 0.
- **TC-G4-EVAL-05** — Given a fixture where one threshold (e.g. faithfulness
  0.78 < 0.80). Then the gate blocks and the report names the failed metric, the
  observed value, and the expected threshold. (mandatory must-fail)
- **TC-G4-EVAL-06** — GITHUB: a prompt-change PR whose eval regresses is blocked;
  the report is attached as the check output.

### Gate 5 — Regression gate

> Every change runs the **full prior test suites**; any regression blocks the
> merge.

**Definition (decided here):** "prior suites" = the entire offline `pytest` suite
(`tradingagents/tests/**` + `tests/req/**` + `tests/security/**`, integration
excluded) plus the gate self-tests in `test-cases` conformance scripts. The
baseline is "green on `master`"; a change that turns any previously-passing test
red is a regression.

**Tests may be modified or deleted** by a branch (no approval needed to edit a
test). Deleting a previously-passing test is allowed only when an approval record
in `docs/approvals` lists that test under `deletes`; an unapproved deletion
blocks. (Deleting tests must not become a way to hide a red change.)

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-G5-REG-01 | OFFLINE | All prior suites green → pass | pass |
| TC-G5-REG-02 | OFFLINE | A newly failing prior test blocks (negative) | blocked |
| TC-G5-REG-03 | OFFLINE | A newly erroring (collection) test blocks (negative) | blocked |
| TC-G5-REG-04 | OFFLINE | New tests that pass do not count as regression | pass |
| TC-G5-REG-05 | CONFIG | The regression job runs the full suite, not a subset | wired |
| TC-G5-REG-06 | GITHUB | A PR that breaks a prior test cannot merge | merge blocked |
| TC-G5-REG-07 | OFFLINE | Deleted test without approval blocks (negative) | blocked |
| TC-G5-REG-08 | OFFLINE | Deleted test with deletion approval passes | pass |

- **TC-G5-REG-01** — Given the full suite on a clean tree. Then exit 0.
- **TC-G5-REG-02** — Given a change that fails one previously-passing test. Then
  blocked; report names the test id. (mandatory must-fail)
- **TC-G5-REG-03** — Given a change introducing an import/collection error. Then
  blocked (collection errors are regressions, not skips). (must-fail)
- **TC-G5-REG-04** — Given a PR that adds a new passing test. Then not counted as
  regression; passes.
- **TC-G5-REG-05** — CONFIG: parse the job; assert it runs the whole suite
  (no `-k`/path narrowing) and fails on any non-zero exit.
- **TC-G5-REG-06** — GITHUB: real PR breaking a prior test; required check fails;
  merge disabled.
- **TC-G5-REG-07** — OFFLINE: a previously-passing test that is now absent and not
  listed in any approval `deletes` blocks, reason `deleted without approval`.
- **TC-G5-REG-08** — OFFLINE: the same deletion with an approval listing it under
  `deletes` passes.

### Gate 6 — AI-use log gate

> A pull request that changes code or prompts without updating the AI-use log is
> blocked.

**Artifact (must be built):** `docs/ai-use-log.yaml` with append-only entries
(`date`, `change_id`, `agent_session`, `summary`, `files_changed`). Rule: if the
PR changes code (`**/*.py` outside docs/tests-only) or prompts (`prompts/**`,
prompt strings), then `docs/ai-use-log.yaml` must also change in the same PR,
adding **at least one new entry**.

> The `change_id` is informational (a stable id such as a PR number, branch name,
> or a hand-written id). The gate does **not** require it to equal the head SHA:
> a commit adding the log entry changes the head SHA, so a SHA match is circular
> and can never be satisfied.

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-G6-AILOG-01 | OFFLINE | Code change + a new log entry passes | pass |
| TC-G6-AILOG-02 | OFFLINE | Code change + unchanged log blocks (negative) | blocked |
| TC-G6-AILOG-03 | OFFLINE | Prompt change + unchanged log blocks (negative) | blocked |
| TC-G6-AILOG-04 | OFFLINE | Docs-only PR needs no log update | pass |
| TC-G6-AILOG-05 | OFFLINE | Log touched but no new entry blocks (negative) | blocked |
| TC-G6-AILOG-06 | GITHUB | PR changing code with stale log cannot merge | merge blocked |

- **TC-G6-AILOG-01** — Given a code diff and a new log entry in the same PR. Then
  pass (the entry's `change_id` value is not checked).
- **TC-G6-AILOG-02** — Given a code diff and no log change. Then blocked, reason
  `AI-use log not updated`. (mandatory must-fail)
- **TC-G6-AILOG-03** — Given a prompt change and no log change. Then blocked.
  (must-fail)
- **TC-G6-AILOG-04** — Given a docs-only PR. Then the gate is not applicable;
  passes.
- **TC-G6-AILOG-05** — Given the log file modified but with no new entry added.
  Then blocked (a touch without an entry is not evidence).
- **TC-G6-AILOG-06** — GITHUB: a code PR with untouched log is blocked.

### Gate 7 — Ownership gate

> A Part claimed in `test-cases/ownership.yaml` (`enabled: true`) has its tests as
> a commitment: any skip or failure blocks. Unclaimed Parts may skip (work not
> started). Claiming is manual, per Part, done in the developer's branch.

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-G7-OWN-01 | OFFLINE | Unclaimed Part may skip | pass |
| TC-G7-OWN-02 | OFFLINE | Claimed Part's skipping test blocks (negative) | blocked |
| TC-G7-OWN-03 | OFFLINE | Claimed Part's passing tests pass | pass |
| TC-G7-OWN-04 | OFFLINE | Claimed Part's failing test blocks (negative) | blocked |
| TC-G7-OWN-05 | OFFLINE | Claimed Part with no collected outcomes blocks (negative) | blocked |
| TC-G7-OWN-06 | GITHUB | PR claiming a Part without implementing it blocks | merge blocked |

- **TC-G7-OWN-01** — Unclaimed Part's `skipped` outcomes are ignored.
- **TC-G7-OWN-02** — A claimed Part test whose outcome is `skipped` is a violation.
- **TC-G7-OWN-03** — A claimed Part whose tests all `passed` passes.
- **TC-G7-OWN-04/05** — `failed`/`error`, or no outcomes at all for a claimed
  Part, block.
- **TC-G7-OWN-06** — GITHUB: flips `part1.enabled: true` without implementing;
  requirements tests stay skipped; merge blocked.

---

## 3. Deployment-strategy and branch-protection cases

These test the model in §0 and PDF's branch-protection clause. Mostly CONFIG /
GITHUB.

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-G7-STRAT-01 | CONFIG | All six gates defined once, on master | present |
| TC-G7-STRAT-02 | CONFIG | PR layer uses master rules, checks PR head code | wired |
| TC-G7-STRAT-03 | CONFIG | Branch self-check reuses master rules (no local copy) | wired |
| TC-G7-STRAT-04 | GITHUB | Branches are isolated (no cross-branch state) | isolated |
| TC-G7-STRAT-05 | CONFIG | Gate scripts taken from master, not PR head (anti-bypass) | wired |
| TC-G7-SELFTEST-01 | OFFLINE | Layer-1 failure warns but does not block | non-blocking |
| TC-G7-SELFTEST-02 | OFFLINE | Layer-2 failure blocks | blocking |
| TC-G7-STRAT-06 | GITHUB | Editing gate config in a PR requires approval | protected |
| TC-G7-BP-01 | CONFIG | Branch protection requires passing CI | required |
| TC-G7-BP-02 | CONFIG | Safety-path change requires human review + ADR | required |

- **TC-G7-STRAT-01** — CONFIG: all six gate scripts/jobs exist under master and are
  referenced by one reusable workflow; no gate is defined only on a feature branch.
- **TC-G7-STRAT-02** — CONFIG: the layer-2 entry is `on: pull_request: branches:
  [master]`; the workflow `uses` comes from base (master), checkout of code is the
  PR head. Asserts the dual "master rules + head code" wiring.
- **TC-G7-STRAT-03** — CONFIG: any branch's self-check references the master
  reusable workflow (`uses: <repo>/.github/workflows/gates.yml@master`) rather than
  an inline/duplicated rule. A branch with no stub still gets checked at PR time.
- **TC-G7-STRAT-04** — GITHUB: two branches run concurrently; each run's artifacts
  and cache are its own; neither reads the other's workspace. Asserted by artifact
  names scoped per run and a cache-key test.
- **TC-G7-STRAT-05** — CONFIG (anti-bypass): the layer-2 workflow checks out
  `master` for `scripts/gates/**` and the PR head for the code; the gate executes
  the master copy. A test greps the workflow for this two-checkout pattern.
- **TC-G7-SELFTEST-01** — OFFLINE: with a known-failing input, the layer-1 path
  reports failure but exits success (warn only); the PR is unaffected. This
  encodes "branch self-check does not block".
- **TC-G7-SELFTEST-02** — OFFLINE: the same failing input on the layer-2 path
  exits non-zero; the required check fails. Encodes "PR check blocks".
- **TC-G7-STRAT-06** — GITHUB: a PR editing `.github/workflows/**` or
  `scripts/gates/**` cannot merge without an approving review from a gate owner
  (protected-path rule), matching "changes to gate config need approval".
- **TC-G7-BP-01** — CONFIG: branch protection on `master` requires the six gate
  checks as required status checks before merge.
- **TC-G7-BP-02** — CONFIG: a protected-path rule requires at least one human
  approval plus a linked architecture decision record for changes under the
  safety-relevant paths (same list as Gate 2).

---

## 4. What must exist before these can be implemented (dependencies)

These cases presume artifacts that do not exist yet. Implementation order:

1. **Approval evidence format** — `docs/approvals/*.yaml` schema (Gate 1).
2. **Static-analysis toolchain** — a type-checker and a dependency auditor wired
   in `ci.yml`, plus the safety-path list (Gate 2).
3. **Requirements registry** — `docs/req/requirements.yaml` + `req-schema.json`,
   generated from `requirements-final.md` (Gate 3).
4. **Fixed eval set + offline harness** — `eval/fixed_set.jsonl`, `eval/harness.py`
   reusing the QUAL metrics (Gate 4).
5. **AI-use log** — `docs/ai-use-log.yaml` + append rule (Gate 6).
6. **Reusable workflow + layer-1 stub** — `.github/workflows/gates.yml`
   (`workflow_call`) and the thin branch stub (strategy).
7. **Gate scripts** — `scripts/gates/check_*.py`, each unit-testable, so every
   OFFLINE case above runs under pytest (strategy).

`ci.yml` today only has lint + tests + clean-install; it implements part of Gate 2
and a kernel of Gate 5, nothing else.

---

## 5. Traceability matrix

| Gate / area | Cases | PDF clause |
|---|---|---|
| Gate 1 Test approval | TC-G1-APPROVAL-01..06 | §6.1 |
| Gate 2 Static analysis | TC-G2-STATIC-01..07 | §6.2 |
| Gate 3 Schema | TC-G3-SCHEMA-01..06 | §6.3 |
| Gate 4 Semantic eval | TC-G4-EVAL-01..06 | §6.4 |
| Gate 5 Regression | TC-G5-REG-01..06 | §6.5 |
| Gate 6 AI-use log | TC-G6-AILOG-01..06 | §6.6 |
| Gate 7 Ownership | TC-G7-OWN-01..06 | claim (strategy) |
| Strategy / layers / isolation | TC-G7-STRAT-01..06, SELFTEST-01..02 | §6 (strategy) |
| Branch protection | TC-G7-BP-01..02 | §6 (branch protection) |

Total: 6 gates + ownership + strategy + branch protection, 52 cases.
