# CS5351 Agentic Software Engineering Project Report

**Project:** TradingAgents enhancement (multi-agent LLM trading-research pipeline)
**Repository:** https://github.com/adnfakw123dfkaj/SEP

## Team members and relative contribution

Contribution is measured by actual productive effort (story points / hours
agreed by the team), normalised so the mean is 1.0. Marks are pro-rated
accordingly, bounded for extremes.

| Member | Student ID | Primary responsibility | Effort | Relative contribution |
|---|---|---:|---:|---:|
| CHEN Yanyan | 60261455 | Part 5 — Security & rating authority | 95 | 0.95 |
| LUO Chen | 60480455 | Requirements analysis, blocking-gate framework, architecture & governance artifacts, Part 3 alignment | 110 | 1.10 |
| ShiYuxin | 61020264 | Part 4 — Data resilience & point-in-time integrity | 95 | 0.95 |
| WANG Shangke | 60050652 | Part 2 — Structured debate & debate quality | 95 | 0.95 |
| ZHU Xiaotong | 60811120 | Part 1 — Config profiles & preflight | 95 | 0.95 |
| CHEN Yiyang | 60915756 | Part 6 — Performance & cost, six-part integration & verification | 110 | 1.10 |

Total effort 600, mean 100. Relative contribution = effort ÷ mean. Sum of
weights equals the number of members (6.0).

---

## 1. Project overview

We enhanced TradingAgents, a LangGraph multi-agent stock-research prototype, into
a system that is faster, cheaper, safer, auditable, and supervised. The application
turns a ticker and an analysis date into a 5-tier rating (Buy/Overweight/Hold/
Underweight/Sell) or `REVIEW`, plus the reports behind it, through analysts →
bull/bear research debate → research manager → trader → risk debate → portfolio
manager. The original had four problems confirmed by measurement: it was slow
(one analyst ≈ 425 s, two ≈ 550 s), token-hungry (no cost accounting), its
sub-agent debate was casual free text, and it had serious correctness/safety
gaps (look-ahead data leaks, non-deterministic rating authority, prompt-injection
surface, no atomic records).

We organised the work into six decoupled Parts, each owned by one member, bound by
frozen shared contracts:

1. **Part 1 — Config, profiles, input gate:** Quick/Standard/Deep profiles,
   `--profile` overrides recorded in the manifest, and a ticker/data preflight that
   fails fast before any LLM call.
2. **Part 2 — Structured debate:** typed `DebateTurn` protocol with validation,
   one retry then graceful degradation, convergence early-stop, transcript export,
   and four deterministic debate-quality proxies.
3. **Part 3 — Evidence, report, records:** `EvidenceRef` on substantive claims, a
   per-run `RunManifest`, a report-fidelity checker, and atomic/idempotent
   decision records.
4. **Part 4 — Resilience & point-in-time:** per-profile checkpoints, data-class
   TTL caching with provenance, bounded retry → cache → `<unavailable>` → `REVIEW`
   degradation, and end-to-end point-in-time integrity.
5. **Part 5 — Security & rating authority:** a deterministic commit gate for the
   rating, sanitisation of untrusted input before prompts, output validation,
   role-bounded tool calls, and no secret leakage.
6. **Part 6 — Performance & cost:** tiered token budgets with a pre-call hard stop,
   per-profile input trimming, per-agent cost accounting and reporting, and latency
   benchmarking.

Beyond the six Parts, a cross-cutting **blocking-gate framework (G1–G7)** was built
on `master`: test approval, static analysis, schema validation, semantic
evaluation, regression, AI-use log, and ownership, with a two-layer model (branch
self-check warn-only, PR-to-master blocking) and branch isolation.

## 2. Requirements engineering process

We started from a measured baseline and an Osborne brainstorming pass (diverge
without criticism, then converge on impact, feasibility, machine-verifiability,
architectural significance, and risk). Every requirement was forced into a
machine-checkable form — an ID, a type (functional/invariant/quality/performance/
cost/governance/security), a statement, a **fit criterion** (metric + threshold +
verification command), a MoSCoW priority with an explicit tradeoff, and a source.
The registry lives in `docs/req/requirements.yaml` with a JSON schema, and a
readable Chinese baseline in `docs/req/requirements-final.md`.

We deliberately **discarded** requirements we could not make machine-verifiable or
finish in the cycle (e.g. full intent classification, an LLM-judged semantic
metric, hashing-chain audit), rather than smuggling them in. This decision helped
exactly where it mattered: the Part 6 acceptance later had to be corrected because
part of the cost routing was implemented but not wired into the run path — a
distinction the requirements format made visible (`status: partial`).

During the project we moved from 15 to 14 requirements as we merged overlapping
items and removed ones the evidence did not support. This **requirement
volatility** was healthy: each merge was tied to a concrete finding (a duplicate
invariant, an unmeasurable quality claim, an over-broad "every sentence" citation
rule) and recorded in the discard list.

## 3. Architecture process

The key architecture decision (ADR-002) was to keep LangGraph as the orchestration
substrate and to separate **advisory** AI from **authoritative** deterministic
code. Agents produce text; a composition root (`graph/trading_graph.py`) is the
single writer of the run record and the rating, with `rating_authority.py` defining
a deterministic commit gate. We evaluated alternatives (single monolithic agent,
multi-process agents, deterministic rule engine) in a candidate evaluation table and
rejected them for auditability, cost, and synthesis reasons. The registered invariants
(REQ-INV-001..004: atomic/idempotent records, point-in-time integrity, deterministic
rating authority, no secret leakage) became zero-tolerance constraints enforced in
code, each with a negative test.

Part 5's ADR-001 fixed the security/rating boundary first: Part 5 owns the rating
and security modules and must not reach into the graph or records; integration is an
adapter plus documented call sites. Naming that boundary up front is what kept the
work reviewable while other Parts ran in parallel.

## 4. How the team used the coding agent

Each member ran a **supervised** AI session: the agent read the requirements, tests,
ownership and gate rules, then proposed a plan that the human approved before any
code. Work was divided into small stages, each paused for review. The session
records (D5) are the primary evidence of human direction. The common pattern that
emerged:

- **Plan before code.** Agents were required to state requirements, interfaces,
  scope, tests (including at least one negative test), and ordered steps, and to
  stop for approval.
- **Small, verified steps.** Each step ended with lint, type check, and the
  relevant tests; the human reviewed before the next step.
- **Demand evidence, not summaries.** Claims like "done" were treated as
  hypotheses. Several genuine defects were caught this way — the child-logger
  redaction blind spot, a provenance bypass on re-commit, a self-referential
  security metric, a `dependencies` check misread because its real exit was hidden
  behind a `tail` pipe, and a cost guard swallowed by the callback layer until a
  real run exposed it.
- **Scope discipline.** Where a fix crossed into a shared component, the agent was
  told to document a handoff instead of editing another Part without approval.
- **Owner-only live testing.** Real-model and integration runs were reserved for
  the human owner; the agent fixed the test harness but did not pretend that a
  skipped live test was a pass.

## 5. How we optimised the process

The process itself was iterated, not just the code:

- **Contract-first parallelisation.** Freezing shared contracts in week 1 let six
  Parts proceed concurrently without waiting on each other's implementations;
  adapters and stubs absorbed the gaps.
- **Gates as process, not paperwork.** The blocking gates turned "the tests are
  green" into something a reviewer can believe: test-approval before
  implementation, regression against a recorded baseline, schema validation of the
  registry, semantic evaluation on prompt/model change, an AI-use log, and per-Part
  ownership. Branch isolation meant unmerged work never polluted another Part's
  verification.
- **Convert a failure into a guard.** Each real defect (look-ahead leak, non-atomic
  record, swallowed budget exception, misclassified check) became a regression test
  or invariant, so the class of bug cannot recur silently. This is where defect
  trends dropped.
- **Results-first review.** Reviewers inspected manifests, evidence, ratings and
  cost reports on disk rather than reading the agent's prose, which caught the
  "passes tests but never called in production" class of problem.
- **Centralised, reviewable gate configuration.** The gate rule set lives only on
  `master`; branches inherit it and carry only a thin self-check stub, so a branch
  cannot weaken the rules it is checked against.

## 6. Process quality evidence

- **Requirement volatility:** 15 → 14 requirements, with each change tied to a
  concrete finding and recorded in the discard list. Volatility was low after the
  first freeze and driven by evidence, not scope creep.
- **Defect trends:** the highest-severity defects were concentrated in the
  integration boundary (not in isolated modules) — look-ahead leaks from live
  social feeds, non-deterministic rating, swallowed budget enforcement, and gate
  checks that failed only in CI. Each was converted into a regression test/invariant,
  and later review rounds on the same areas produced no recurrences.
- **Ambiguity resolution:** the debate protocol, point-in-time boundaries, and
  cost-routing semantics were resolved by asking before implementing (e.g. peak
  vs off-peak CNY pricing, holiday policy, degradation vs hard-stop), which reduced
  rework in those Parts.
- **Verification compliance:** the offline suite (`pytest tests -m "not
  integration"`) is the CI path; live/integration tests (12) are owner-run. Gate
  self-tests (G1–G7) run in CI. Every invariant has a negative test.
- **Honest scope:** several requirements are marked `partial` where the code exists
  but is not fully wired (e.g. Part 6 summarise/cheaper-model routing), and the
  report does not claim final acceptance for them.

## 7. Limitations

- Some Parts are integrated to different depths; Part 3's claim-level evidence and
  Part 6's progressive cost routing remain partially wired.
- The repository is public and `master` is protected by an active GitHub
  ruleset: pull requests are required, and the required status checks include
  `gate self-tests` plus G1–G7; deletion and non-fast-forward updates are
  blocked. The ruleset does not currently require a separate approving review
  for safety-critical paths; that remains a documented human-review and ADR
  obligation rather than a GitHub-enforced rule.
- Real Quick/Standard/Deep benchmarks and optimisation are measured but not fully
  brought under the original token targets; debate/risk history compression is the
  main remaining cost lever.

---

## 8. Self-reflections

### CHEN Yanyan (60261455) — Part 5: Security & Rating Authority

When I started Part 5, my first job was not to write code but to bound it. I had
the agent read the requirements registry, my Part's test cases, the ownership file
and the gate rules before proposing anything, and I required it to stop and present
a plan — gaps, files, interfaces, failure semantics, verification — for my
approval. I also fixed the interface boundary up front: Part 5 owns
`contracts/rating.py`, `rating_authority.py` and `security/`, exposes a single
deterministic commit entry (`commit_rating`), and may not touch the Part 1 graph or
Part 3 records; integration was delivered as an adapter plus documented call sites.
Naming those boundaries early is what kept the work reviewable.

Reviewing was iterative, and several of my corrections were about governance, not
style. When I tested log redaction, the filter was on the root logger; a logger
filter does not see records propagating up from child loggers, so I required
handler-level installation with a test emitting a registered key from a child
logger. The commit path let a repeated submission pair an existing record with the
caller's current provenance and return success, and a corrupt "Buy" record could
still surface as tradeable; I demanded fail-closed corruption, request-provenance
validation before idempotency, and tests that assert the rating and that nothing
was written. The injection "block rate" graded the detector with itself; I had it
reworked around independent fixture labels plus a reverse control, so disabling
detection must make acceptance fail. When a static check reported
`dependencies=false`, I pushed to read the code that classifies it and found it is
an always-required check, that the real cause was an uninstalled interpreter, and
that the true script exit was hidden by a `tail` pipe. Each time, the evidence
drove the design.

What this taught me is that green tests, actual behaviour, and completed
integration are three different claims. My suite was green long before the module
was genuinely safe, and even now the module is not fully integrated into the Part 1
graph and Part 3 records. Several problems — the child-logger blind spot, the
provenance bypass, the self-referential metric, the misinterpreted `dependencies`
result — were found by my review, not by the agent's self-check. Next time I would
front-load adversarial negative tests and a per-round approval/time model before
coding, and treat any "pass" as a claim to be falsified rather than a result to
trust.

### LUO Chen (60480455) — Requirements analysis, gate framework, architecture & governance

My main contribution was the blocking-gate framework and the analysis behind it. I
read the codebase and wrote `ta-details.md` mapping the agents, tools, vendors and
failure paths and ranking the defects; from that I derived the requirements and
designed the G1–G7 gates, implemented the gate scripts, CI workflows and support
artifacts, and built the D2/D3/D4 architecture and governance documents.

The most valuable thing I learned was how to work with a coding agent. Early on I
gave broad instructions and got plausible output I could not easily check. I learned
to ask for plans first, to break work into small verifiable steps, and to demand
evidence rather than summaries. The clearest example was when I was asked to look
critically at a "finished" part and found it was never actually used by the running
program. That changed how I direct an agent: I now treat its confident report as a
hypothesis and verify it myself.

This project also changed how I understand software engineering. I used to think of
requirements, architecture, testing and review as paperwork around the real work.
Building the gates showed the opposite: together they are how you make an
AI-assisted process trustworthy. A passing test proves one function works; it does
not prove the system uses it correctly. If I did this again I would set up the
review and evidence structure before writing features and keep the human
checkpoints in place from the first step. The biggest growth was that shift — from
asking the agent to produce code to supervising it like a fast junior whose work
counts only once verified.

### ShiYuxin (61020264) — Part 4: Data resilience & point-in-time integrity

Part 4 was assigned to me by the team leader. I began by reading the implementation
plan alongside the repository, because I needed to understand what already existed
before deciding how to proceed. Date-window handling and SQLite checkpoints already
existed; caching and fallback were less complete, and some requirement tests were
only placeholders. This told me the work would involve both adding missing pieces
and checking how they fit into the existing application.

I used Codex to help inspect the code, develop the implementation, and run tests. I
reviewed the results and asked for further work when changes were incomplete; in
particular I wanted the cache and fallback work connected to real data paths and the
tests to check behaviour rather than merely confirm a module could be imported. The
detailed implementation was AI-assisted; my contribution was taking responsibility
for the assigned area, keeping the work aligned with the plan, and reviewing progress
and test results.

Testing was useful because it revealed issues that were not obvious from the plan:
cache isolation, Windows file locking, and compatibility with existing state-log
behaviour. After those fixes the full project run reported 1716 passed and 33
skipped, and the Part 4 run 59 passed. These results show the tested paths work, but
they do not establish every target. The repository still lacks Standard/Deep
checkpoint defaults in profile config, the complete Part 3 manifest workflow is
outside this implementation, and production cache-hit rates, a network baseline and
fault-injection demonstrations were not archived. I will identify Codex accurately
in the session record. Overall this task gave me practice in carrying an assigned
module through inspection, AI-assisted implementation, testing, and documentation.

### WANG Shangke (60050652) — Part 2: Structured debate & quality

In Part 2 I was responsible for the structured debate protocol and its quality
proxy metrics. This work showed me that vibe coding is not simply asking an AI agent
to generate code. Effective AI-assisted development needs clear requirements, strict
file boundaries, stable interface contracts, and measurable acceptance criteria. I
divided the work into stages: freeze the `DebateTurn` and `DebateTranscript`
contracts, implement validation and retry, integrate convergence and transcript
export, then add deterministic quality metrics.

The implementation covered schema validation, a single retry then graceful
degradation, maximum-round enforcement, convergence-based early stopping, and four
quality indicators: evidence coverage, rebuttal coverage, unsupported-claim rate,
and duplicate-claim rate. I used offline fixtures and fault injection for
deterministic edge cases, because invalid JSON or repeated model non-compliance
cannot be reproduced reliably with a live model, then used thirty real LLM
transcripts to confirm the schema and quality thresholds on the success path.

Several difficulties improved my understanding. I had to distinguish the
repository's pre-written gate tests from the behavioural assertions still to be
implemented. More importantly, I found that the existing Research Manager rebuilds
the nested debate state and may discard the new `turns` and `quality_available`
fields. This was outside my isolated Part 2 scope, but it demonstrated that passing
module-level tests does not guarantee end-to-end integration. I documented it for
the integration owner instead of modifying a shared component without approval.
Overall, AI can accelerate implementation and test generation, but the developer
remains responsible for interpreting requirements, controlling scope, reviewing
evidence, and communicating integration risks.

### ZHU Xiaotong (60811120) — Part 1: Config profiles & preflight

Working on Part 1 taught me that adding a command-line option is only a small part
of delivering a reliable feature. The Quick, Standard and Deep profiles needed a
clear contract, a consistent mapping to existing configuration, and tests showing
the chosen profile reached the run configuration. I first focused on implementing
the profile values, but the integration tests exposed a precedence bug: the existing
research-depth selection could overwrite the profile's round limits. That was a
reminder to test the complete configuration path rather than a helper function in
isolation.

The preflight work changed how I think about boundaries. A ticker can be
syntactically valid while its market data is unavailable, so those outcomes must be
represented separately. My first implementation reached directly into a vendor
library; the repository's layering test caught this and I redirected it through the
existing dataflow router, which preserved the architecture and made the behaviour
testable with deterministic fakes.

Human review and CI evidence found gaps local feature tests did not show. The first
full CI run flagged a missing test-approval record, lint formatting, a test
importing a dependency not available in the matrix, and a missing AI-use-log update.
These failures showed that verification includes process requirements as well as
functional behaviour. In particular, an approval recorded after implementation
cannot honestly be represented as pre-approval. Future work should begin with a
reviewed test plan and approval record before code changes.

### CHEN Yiyang (60915756) — Part 6: Performance & cost, integration & verification

My main responsibility was Part 6 (performance and cost control), followed by
integration of the six parts and end-to-end verification. I built the cost-tracking
path, the pre-call budget guard, the quality gate, and the acceptance tooling. I
began treating the agent mainly as a fast implementer and learned that speed is not
the difficult part; keeping the implementation aligned with requirements, evidence,
and human decisions is.

One example changed my approach. The first low-budget live run appeared guarded, but
the callback exception was swallowed by LangChain and the graph continued far over
budget. Only a real provider run exposed it, and the evidence checks also failed on
the CLI streaming path even though offline tests passed. I therefore stopped treating
local unit tests as proof of integration, added real smoke runs, checked manifests,
evidence, ratings and cost reports on disk, and moved the budget guard outside
callbacks. I also separated measurement from acceptance: a quality score built on the
same cost report is not independent evidence, so I introduced a second cost
calculation, claim-level evidence, numeric checks against a verified snapshot, and
explicit unavailable cases.

I made process mistakes too. I integrated some work directly on master, which
weakened the pull-request history; I now understand why the course emphasises
branch-based review and traceable decisions, and I corrected it with retrospective
review records and a separate PR path, though the original history cannot be
recreated honestly. In future work I will create the review structure before
implementation and keep evidence collection part of each change.

---

## 9. Extended engineering evidence

This section supplements Sections 1-7 with the evidence that is too detailed for
the main narrative. It does not replace the original account, and it does not
change the self-reflections in Section 8.

### 9.1 Scope and integration map across the six Parts

The project was divided into six Parts so that work could proceed in parallel
without changing the shared contracts. The map below records what each Part owns
and how far it is integrated. The integration depth is deliberately stated rather
than implied: a module that passes its own tests is not the same as a module that
is wired into the running CLI.

| Part | Primary owner | Main requirements | Implemented evidence | Integration depth |
|---|---|---|---|---|
| Part 1 | ZHU Xiaotong | REQ-FR-001, REQ-FR-002 | `profiles.py`, `preflight.py`, profile and preflight tests | Integrated into CLI and graph setup |
| Part 2 | WANG Shangke | REQ-FR-003, REQ-QUAL-001 | Typed debate contract, validator, convergence, quality proxies, transcript export | Integrated into research debate |
| Part 3 | LUO Chen (alignment) | REQ-FR-004, REQ-QUAL-002, REQ-INV-001 | Evidence registry, manifest writer, report index, atomic/idempotent records | Integrated through the composition root |
| Part 4 | ShiYuxin | REQ-FR-005, REQ-INV-002 | TTL cache, checkpoint/resume, fallback events, point-in-time filters | Integrated below the agent layer |
| Part 5 | CHEN Yanyan | REQ-INV-003, REQ-SEC-001, REQ-INV-004 | Rating authority, input sanitisation, output validation, tool guard, redaction | Integrated at the commit and dispatch boundaries |
| Part 6 | CHEN Yiyang | REQ-COST-001, REQ-PER-001 | Token accounting, profile budgets, pre-call hard stop, quality floor, benchmark tooling | Partially integrated; progressive routing remains open |

The six Parts share contracts rather than implementation details. The composition
root is the only writer of authoritative run state and the final rating. Analysts,
researchers, the trader and the risk analysts remain advisory: they produce
reports and recommendations, but they do not commit the rating.

### 9.2 Requirements volatility and the two discarded external requirements

The registry contains **14 top-level requirements**. If the discarded
source-requirement identifiers are counted as well, the full YAML contains 16
`REQ-*` identifiers. The difference is intentional: the two `-other` entries are
not accepted product requirements. They are kept in the `discarded:` section to
preserve the decision trail.

| Identifier | Source | Original idea | Disposition | Implemented? |
|---|---|---|---|---|
| `REQ-FR-01-other` | other-doc | Full intent classification, including off-topic or ambiguous requests | Replaced by `REQ-FR-002` | Not separately implemented; the ticker/data preflight covers the critical validity check |
| `REQ-FR-03-other` | other-doc | Ambiguous-request clarification and a human handling path | Discarded | No; it would require UI, queue and human SLA work outside the course cycle |

`REQ-FR-01-other` was not "lost". Its useful core was narrowed into the
preflight requirement: before any LLM call, the system validates that the ticker
is a real instrument and that recent price data is available. This prevents the
most expensive failure without paying for a separate classifier. `REQ-FR-03-other`
was a deliberate non-goal: the product is a CLI research tool, not a support desk,
so a clarification workflow and human queue were not built.

The main volatility event was a reduction from 15 to 14 accepted requirements.
The changes were driven by evidence, not by convenience:

| Change | Reason | Evidence / consequence |
|---|---|---|
| Merge duplicated invariant wording | Two entries described the same zero-tolerance rule | One invariant and one negative test remain |
| Drop an unmeasurable quality claim | The proposed metric could not be checked deterministically | Replaced by the claim-level and numeric checks in `REQ-QUAL-002` |
| Narrow "every sentence" citation | The original wording would have imposed an unbounded token cost | Claim groups now carry evidence refs without requiring a citation on every line |
| Keep `REQ-COST-001` as `partial` | Cost routing exists but is not fully wired into the runtime graph | The report states the gap instead of claiming acceptance |

This is the distinction the project treats as important: a requirement is not
done because code exists, and a requirement is not met because a test says
"pass". The fit criterion has to be exercised on the real path.

### 9.3 Architecture alternatives and authority decisions

The main architecture decision was to keep LangGraph as the orchestration
substrate while separating advisory AI from authoritative code. The alternatives
were evaluated against auditability, cost, latency and synthesis quality.

| Alternative | Why it was considered | Why it was not chosen |
|---|---|---|
| Single monolithic agent | Simplest implementation | No independent perspectives, no bounded per-role cost, hard to audit |
| Multiple processes per agent | Strong isolation | Shared graph state and LLM latency dominate; process overhead adds no useful isolation |
| Deterministic rule engine only | Fully reproducible | Cannot perform news/fundamental synthesis; the project requires a genuine AI component |
| LangGraph with a composition root | Typed state, parallel analysts, bounded debates, one authority boundary | Chosen; the cost is non-determinism, mitigated by the rating gate and `REVIEW` |

ADR-001 fixed the Part 5 boundary first: Part 5 owns the rating and security
modules but may not reach into the graph or the records. ADR-002 records the
multi-agent pipeline, the layered context, the budget cap and the re-injection of
protected constraints. The result is a single write path for the rating and a
separate, testable commit gate.

The runtime policy is fail-closed, not "best effort":

- If provenance is missing or invalid, the rating is `REVIEW` and nothing is
  written.
- If a budget projection would exceed the profile hard cap, the run stops before
  the provider call and is recorded as `budget_exceeded`.
- If a tool is not allowed for a role, the guard rejects it before execution and
  records a security event.
- If a data source is unavailable, the report must say so; it must not invent a
  numeric value.

### 9.4 Context assembly, tool budgets, and the compaction boundary

Every model turn receives a layered context: identity, standing constraints,
retrieved knowledge, conversation or debate history, resumable state, and the
current task. The context is assembled per node, and the identity and standing
constraints are never removed by the trimming that applies to tool and report
bodies.

The profile budgets are intentionally explicit:

| Profile | Analysts | Research / risk rounds | Hard token cap | Tool-output cap | Report-context cap | Output cap |
|---|---|---:|---:|---:|---:|---:|
| Quick | market | 1 / 1 | 80,000 | 2,000 chars | 1,000 chars | 1,024 |
| Standard | market, news, fundamentals | 1 / 1 | 150,000 | 3,500 chars | 2,000 chars | 2,048 |
| Deep | market, social, news, fundamentals | 2 / 2 | 300,000 | 5,000 chars | 3,000 chars | 3,072 |

There are two different things in this table. The token cap is a budget guard
measured from provider usage. The character caps are context-compression controls
that limit how much tool output and how much prior report text are injected into a
prompt. The latter is visible in the final report when the Market Analyst says the
stock-data CSV was truncated.

Compaction is implemented in the cost layer and is used by audit tooling, but it
is **not wired into the runtime path**. The runtime currently stops hard rather
than degrading silently. This is a deliberate choice: a hard stop to `REVIEW` is
easier to audit than a partially summarised analysis that looks complete. The
next engineering step is to connect summarisation and cheaper-model routing to
the runtime, with protected evidence keys kept verbatim.

### 9.5 Blocking gates and failure prevention

The gate framework uses one set of rules owned by `master`. A branch push is
warn-only; a pull request to `master` is blocking. The repository is public, and
`master` is protected by an active GitHub ruleset. The required status checks are
the gate self-tests and G1-G7. Deletion and non-fast-forward updates are blocked.

| Gate | What it checks | Failure it prevents |
|---|---|---|
| G1 | Tests for the change were approved before implementation | Code written before the test plan is agreed |
| G2 | Lint, type checking, dependencies; contract, security, API and permission checks on safety paths | Unsafe or unauditable code entering a safety boundary |
| G3 | Requirements registry validates against its schema | A registry that no tool can parse or enforce |
| G4 | Prompt/model changes replay a fixed evaluation set against thresholds | A prompt change that degrades quality without evidence |
| G5 | Every prior passing test still passes; deletion requires approval | Silent regressions and disappearing tests |
| G6 | Code or prompt changes include a new AI-use-log entry | Agent-generated changes without a recorded human review trail |
| G7 | A claimed Part's tests pass and do not skip | A Part being marked complete while its tests are skipped or failing |

The ruleset does not currently require a separate approving review for
safety-critical paths. That part of D7 remains a documented human-review and ADR
obligation rather than a GitHub-enforced rule. The report records this limitation
rather than claiming that the platform enforces more than it does.

The gate design also changed the process. A failure is not fixed with a private
patch and a note; it becomes a check, a regression test or an invariant. The gate
self-tests are themselves tested, so a gate that fails for the wrong reason is
treated as a defect.

### 9.6 Recorded Deep run evidence

A recorded Deep-profile acceptance run provides a concrete cross-check of the
system. It is not used as a substitute for the offline test suite; it is used to
show that the integrated path produces the audit fields the design claims.

| Observation | Recorded value | What it demonstrates |
|---|---:|---|
| Profile | Deep | Four analysts, two research rounds, two risk rounds |
| Agent stages | 12 | All downstream roles executed |
| Tokens | 263,940 | Under the 300,000 hard cap |
| Cost estimate | 1.336923 | Per-run cost is measured, not guessed |
| Evidence records | 25 | Tool results are captured with hashes |
| Claim groups | 147 | 95 numeric and 52 qualitative groups |
| Fallback events | 16 | Missing sources are recorded, not hidden |
| Quality floor | passed | Evidence coverage and contradiction checks pass |
| Final rating | Underweight | Committed by the composition root, not copied from an analyst |
| Review required | false | Rating authority accepted the committed value |

The same run also shows the limits of the evidence. Sentiment sources were
unavailable, FRED was not configured, and the report explicitly calls Neutral a
data gap rather than a signal. The market data CSV was truncated by the tool-output
cap. Those are not contradictions in the report; they are the visible trade-offs
of a bounded, point-in-time system.

### 9.7 Defect trend and root-cause analysis

The most serious defects were at boundaries, not inside isolated functions. The
bug diary records five gate-related defects and the project review records show
integration defects around the same themes. The pattern is consistent: a module
can pass its unit tests while the composed system still fails.

| Defect | Symptom | Root cause | Mechanism added |
|---|---|---|---|
| BUG-001 | G2 dependency check failed only in CI | Import path and `sys.modules` shadowing | Check the file on disk, independent of cwd |
| BUG-002 | G1 blocked gate-infrastructure tests | Gate tooling was treated as application tests | Exclude gate infrastructure from approval coverage |
| BUG-003 | G6 parsed YAML as JSON | Wrong parser for the file type | Parse YAML with a safe loader and a fallback |
| BUG-004 | G4 crashed on non-eval changes | Missing default for the metrics argument | Stable payload shape with `metrics=None` |
| BUG-005 | G5 reported a present test as deleted | Brittle node-id comparison across pytest versions | Normalise ids and give fragile parametrisations explicit ids |

The integration defects followed the same lesson. A budget exception was swallowed
by a callback; the fix moved enforcement before the provider call. Evidence was
missing on the streaming path; the fix bound context before graph start. Numeric
claims produced false positives; the fix narrowed the checks to labelled market
values. In each case the response was a mechanism, not a reminder to be more
careful.

### 9.8 Human oversight and transcript evidence

The project used supervised AI sessions. The agent could propose, implement, test
and explain, but it could not approve its own plan, merge its own work, or run
unattended live tests. The transcripts preserve the human interventions that
changed the work:

- A plan was required before code, including requirements, interfaces, scope,
  tests and steps.
- A Part 5 acceptance was rejected when the evidence did not match the claim; the
  follow-up required handler-level redaction, fail-closed provenance and
  independent injection labels.
- A real low-budget run exposed a swallowed callback exception; the human review
  turned that incident into a pre-call enforcement mechanism.
- When a fix crossed a shared component, the agent documented a handoff instead
  of editing another Part without approval.
- Real-model and integration runs were reserved for the human owner; a skipped
  live test was not treated as a pass.

This is why the report distinguishes "the agent wrote code" from "the team
accepted the code". The transcript is evidence of supervision, not a claim that
the agent was autonomous.

### 9.9 Traceability examples

The trace matrix is useful only if it can be followed in both directions. These
examples are representative:

| Requirement | Enforcing component | Test / evidence | Runtime field |
|---|---|---|---|
| REQ-FR-004 | Evidence registry and manifest writer | Evidence/manifest tests | Evidence Index, manifest evidence refs |
| REQ-QUAL-002 | Report fidelity and claim grouping | Report faithfulness tests | Claim Index, unsupported/contradiction metrics |
| REQ-INV-002 | Date windows and vendor withholding | Point-in-time tests | `pit_coverage` |
| REQ-INV-003 | Rating authority and composition root | Rating-invariant tests | Committed rating, `rating_authority` |
| REQ-SEC-001 | Sanitisation, output validation, tool guard | Security regression tests | `security_events` |
| REQ-COST-001 | Guarded LLM and profile budgets | Token/cost tests | `cost_estimate`, `budget_exceeded` |

The chain is not just a diagram. A runtime field can be traced back to the code
and test that produced it, and a requirement can be traced forward to the
artifact that demonstrates it.

### 9.10 Limitations, exit criteria, and next steps

The remaining limitations are specific:

1. **Cost routing:** summarisation and cheaper-model routing are implemented in
   the cost layer but not fully wired into the runtime. `REQ-COST-001` remains
   `partial`, and aggregate p95 is not closed.
2. **Safety-path review:** the public repository ruleset requires PRs and the
   G1-G7 checks, but it does not enforce a separate approval specifically for
   safety-critical paths. That remains a human process and ADR obligation.
3. **D8 layout:** the repository uses a compatibility `src/` and `test/` entry
   point; the application source remains in the package layout. The compatibility
   mapping is documented, and a physical migration is a deliberate future change.
4. **Live evidence:** live provider runs are owner-run and not part of the
   deterministic offline suite. They are acceptance evidence, not a substitute for
   regression tests.
5. **Report length:** this document is a process report, not a full code manual.
   The appended evidence is intentionally selective; the repository remains the
   source of record for code, tests and artifacts.

The exit criteria for the project are therefore: the offline suite is green; the
blocking gates are configured and run from `master`; a real run produces the
expected report, evidence, manifest and rating fields; and every remaining gap is
named with an owner and a next step rather than hidden behind a success claim.

## Appendix A. Artifact index

| Deliverable | Primary location | Purpose |
|---|---|---|
| D1 requirements | `docs/req/requirements.yaml`, `docs/req/req-schema.json`, `docs/req/PRD.md` | Machine-readable requirements, schema and product summary |
| D2 architecture | `architecture-blueprint.md`, `docs/architecture/` | Blueprint, ADRs, invariants, trace matrix, memory, permissions, policies, evaluations |
| D3 governance | `AGENTS.md`, `docs/code-governance/`, `.opencode/`, `.agent/` | Agent rules, module constraints, tool manifest, permissions |
| D4 verification | `docs/code-governance/verification-constraints.md`, `docs/review-memo.md`, `docs/debt-register.md`, `docs/bug-diary.md` | Verification policy, reviews, debt and defects |
| D5 transcripts | `transcripts/` | Annotated supervised sessions |
| D6 report | `Report.md` | This process report and reflections |
| D7 repository | GitHub `adnfakw123dfkaj/SEP` | Source, tests, CI and blocking gates |
| D8 source and tests | `src/`, `test/`, `tradingagents/` | Compatibility entry points and application source |
| D9 prompt | `Prompt.md` | Static supervised startup prompt |

## Appendix B. Verification command index

The offline path is the CI path; live tests are owner-run:

```bash
cd tradingagents
python -m pytest tests -q -m "not integration"
python -m pytest tests -q
ruff check .
pyright
```

The gate logic is exercised from the repository root:

```bash
python -m pytest tests/gates -q
```

The GitHub workflow that runs the blocking gates is
`.github/workflows/ci.yml`, which calls `.github/workflows/gates.yml`. The gate
rules are owned by `master`; a branch cannot weaken the rules it is checked
against.

## Appendix C. Requirement-level acceptance evidence

The following matrix records the primary verification path for each accepted
top-level requirement. It is a summary, not a replacement for the tests or the
requirement registry.

| Requirement | Primary acceptance evidence | Status | Remaining caveat |
|---|---|---|---|
| REQ-FR-001 | Profile matrix and manifest-profile tests | Implemented | Profile limits are enforced per run |
| REQ-FR-002 | Invalid-input zero-call test and preflight benchmark | Implemented | Live ticker coverage depends on the data vendor |
| REQ-FR-003 | Debate schema, max-round and transcript export tests | Implemented | A malformed model output can still require degradation |
| REQ-QUAL-001 | Evidence, rebuttal, unsupported and duplicate proxy tests | Implemented | Proxies are deterministic checks, not human judgement |
| REQ-FR-004 | Numeric/qualitative evidence and manifest schema tests | Implemented | Claim groups are evidence attribution, not semantic proof |
| REQ-QUAL-002 | Numeric contradiction, citation and schema tests | Implemented | Contradiction checks cover labelled market values only |
| REQ-INV-001 | Fault-injection, idempotency and hash-validation tests | Implemented | Single-process idempotency is the supported contract |
| REQ-FR-005 | Resume, duplicate-call, cache and stale-cache tests | Implemented | Cache hit rate depends on the workload and TTLs |
| REQ-INV-002 | Point-in-time tests across prices, news, fundamentals and social data | Implemented | Some historical sources are withheld rather than fetched |
| REQ-INV-003 | Fuzz, provenance, adversarial-text and persisted-revalidation tests | Implemented | The parser is shared with the advisory path |
| REQ-SEC-001 | Injection, tool-guard, validation and event-log tests | Implemented | Fixture-based security rates are not a proof against all attacks |
| REQ-INV-004 | Log, prompt, manifest, report and exception redaction tests | Implemented | External secret scanners remain a CI responsibility |
| REQ-PER-001 | Profile latency benchmark and recorded run timings | Implemented | Live latency varies with provider load |
| REQ-COST-001 | Budget, cost-report and hard-stop tests; recorded Deep run | Partial | Aggregate p95 and progressive routing remain open |

The matrix also makes the dependency direction visible. Feature requirements
depend on the evidence, security and cost requirements; the invariants cut across
all of them. A change that weakens an invariant is therefore not a local change,
even when it touches only one module.

## Appendix D. Residual risks and release checklist

| Risk | Early warning | Mitigation / owner action |
|---|---|---|
| Vendor data disappears or is partial | Fallback count rises; report contains unavailable placeholders | Keep the fallback path; do not replace a gap with a guessed value |
| Model output drifts after a prompt change | G4 semantic metrics change; quality floor fails | Replay the fixed evaluation set; require human review |
| Budget guard is bypassed on a new path | Manifest cost exceeds the profile cap | Exercise the CLI stream path, not only unit tests |
| A claim is supported only by a group-level ref | Claim evidence audit shows weak mapping | Treat this as evidence attribution; add semantic checks only when they can be verified |
| Safety-path review is only procedural | A safety path changes without an ADR or approval | Require human review; consider a path-specific ruleset |
| Report becomes longer but not more evidential | Page count rises while decisions are unchanged | Tie each added page to a requirement, defect, run or gate |

Release checklist:

- [ ] Offline suite green for the changed scope.
- [ ] G1-G7 configuration present for a PR to `master`.
- [ ] Report, manifest, evidence index and claim index present.
- [ ] Quality floor and rating authority pass.
- [ ] Known gaps are marked `partial` or recorded as future work.
- [ ] No secret, token or private key appears in a tracked artifact.
