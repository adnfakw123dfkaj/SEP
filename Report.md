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
- Blocking-gate branch protection cannot be physically enforced on a private
  personal GitHub account (a platform limit); gates run and report, but do not
  block the merge button in that setup.
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
