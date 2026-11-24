# Review Memo

One memo per pull request. Covers spec alignment, architecture alignment, code and
test quality, and operational metadata; security and efficiency are checked
throughout; ends in a verdict: **APPROVE**, **CHANGES REQUIRED**, or **REJECT**.

## Template

```
## PR: <title> (#<number>)   Reviewer: <name>   Date: <YYYY-MM-DD>
### Spec alignment
- Requirements addressed: REQ-... (fit criteria met? evidence?)
- Scope: in-scope only? contracts respected?
### Architecture alignment
- Element↔module mapping (structural-constraints)
- Authority boundaries respected (advisory vs authoritative)
- ADR referenced for any structural/safety change
### Code & test quality
- Lint/type clean; tests added; negative test present; no regressions
- Every fit criterion has a test; invariant tests fail when violated
### Operational metadata
- AI-use log updated (G6); approval present (G1); ownership correct (G7)
- Security: no secrets, injection handled; Efficiency: token/latency sane
### Verdict
- APPROVE / CHANGES REQUIRED / REJECT  (reasons)
```

## Records

> **Retrospective reviews.** The entries below document changes that were
> integrated directly on `master` before the PR workflow was in use. They are
> reconstructed review records with commit ranges, not retroactive GitHub PRs.
> The reviewer is `hhshow`; the final D8/docs change is delivered through a real
> `hhshow` PR.

### PR: Part 6 cost/token alignment (2026-11-22)
- Spec: REQ-COST-001 — corrected requirement text to actual behaviour (hard-stop
  to REVIEW + input trimming + cost report; summarize/cheaper-model routing not
  wired). Fit criteria now point to real `tests/req/test_token_cost.py`.
- Architecture: cost/element mapping unchanged; authority (budget hard-stop) in
  the composition root/GuardedLLM.
- Code/test: rewrote stale require()-skip stubs into offline tests over the real
  audit/budget/enforcement API (8 tests). ruff/pyright clean; no regressions.
- Ops: AI-use-log updated; change is tests+docs only → G1 skipped (no app code).
- Security: n/a. Efficiency: budget caps confirmed (80k/150k/300k).
- Verdict: **APPROVE** (offline); live token/latency to be run by owner.

### PR: D8 layout + D2 architecture (2026-11-22) — retrospective
- Spec: D8 (`src/`, `test/offline`, `test/live`) and D2 (11 artifacts + blueprint).
- Architecture: docs derived from actual code; ADR-002 documents the pipeline,
  layered context, budget caps, and constraint re-injection.
- Code/test: root `src/README.md` is a D8 compatibility entry mapping to
  `tradingagents/tradingagents/` and `tradingagents/cli/`; root
  `test/offline/run.sh` and `test/live/run.sh` delegate to the existing
  `tradingagents/test/*` entry points. Source stays in the package; no duplicate
  source tree. Offline suite remains green.
- Ops: README, debt register, and risk list document the compatibility layer.
  Security: none. Efficiency: n/a.
- Verdict: **APPROVE** (layout mapping); physical `src/` migration remains a
  deliberate future option if the course requires literal source trees.

### PR: Part 1 profiles and preflight (2026-11-22) — retrospective
- Commits: `3e206d2`, `a2ac734`, `b3cde9d`.
- Spec: REQ-FR-001, REQ-FR-002. Named profiles, headless Standard default,
  profile analyst validation, preflight on every run, TTL cache propagation.
- Architecture: profiles resolve at the composition root; preflight remains the
  input gate; no authority boundary changed.
- Code/test: profile, preflight, and CLI integration tests added; full suite green.
- Ops: AI-use log recorded; no secrets. Efficiency: profile defaults and cache
  TTL are the first cost controls.
- Verdict: **APPROVE**.

### PR: Part 3 evidence, manifest, and records (2026-11-22) — retrospective
- Commits: `f85d984`, `921300d`, `524fdca`, `6990eac`.
- Spec: REQ-FR-004, REQ-QUAL-002, REQ-INV-001. Single manifest writer, tool/cache
  evidence refs, report evidence index, idempotent decision records.
- Architecture: Part 3 owns persistence; graph supplies run data; evidence and
  records remain contract-typed.
- Code/test: manifest, evidence, report, and idempotency tests added; full suite
  green.
- Ops: AI-use log recorded; no secrets. Efficiency: atomic writes avoid duplicate
  run records.
- Verdict: **APPROVE**.

### PR: Part 5 security and rating authority (2026-11-22) — retrospective
- Commits: `80273ce`, `399f71b`, `9735e39`, `95373f9`.
- Spec: REQ-INV-003, REQ-SEC-001, REQ-INV-004. File-backed committed ratings,
  deterministic provenance, input sanitization, tool-call guard, output
  validation, log/report redaction.
- Architecture: agents remain advisory; the composition root is the only rating
  writer; guards block rather than decide.
- Code/test: rating-invariant, prompt-injection, and secret-redaction tests added;
  full suite green.
- Ops: security events persist in the manifest; no secrets found. Verdict:
  **APPROVE**.

### PR: Part 4 resilience and point-in-time cache (2026-11-22) — retrospective
- Commit: `431c84e`.
- Spec: REQ-FR-005, REQ-INV-002. Standard/Deep checkpoint defaults, cache-hit
  accounting, Deep-to-Quick LLM fallback, typed fallback events.
- Architecture: cache/checkpoint remain below agents; fallback stays inside the
  LLM tier without changing rating authority.
- Code/test: cache, checkpoint/resume, point-in-time, and fallback suites green.
- Ops: fallback manifest fields recorded; no secrets. Efficiency: cache reuse and
  checkpoint resume are explicit.
- Verdict: **APPROVE**.

### PR: Part 2 structured debate and transcript (2026-11-22) — retrospective
- Commit: `bf480c6`.
- Spec: REQ-FR-003, REQ-QUAL-001. Research Manager preserves turns/quality;
  transcript export resolves evidence without changing the wire contract;
  `debate_transcript.json` and state-log transcript are persisted.
- Architecture: debate state stays typed; evidence resolution is additive.
- Code/test: debate protocol, quality, and graph transcript tests green.
- Ops: AI-use log recorded. Verdict: **APPROVE**.

### PR: Integration hardening and live acceptance (2026-11-22) — retrospective
- Commits: `d72d366`, `c72697b`.
- Spec: cross-Part integration of budget hard fail, evidence stream, rating
  authority, state-log completeness, Windows headless output, cache locking, and
  retained Part 6 artifacts.
- Architecture: pre-call budget enforcement moved outside LangChain callbacks;
  evidence/rating now work on the CLI stream path; no authority boundary moved.
- Code/test: full suite, targeted part6/graph/security tests, and live smoke
  (Deep/Quick) exercised. Verdict: **APPROVE** for integration correctness.

### PR: Acceptance metrics and first optimization (2026-11-22) — retrospective
- Commits: `cb5382b`, `58a8510`.
- Spec: Part 3 claim-level evidence/numeric contradiction, Part 4 vendor/PIT/cache
  metrics, independent cost ground truth, composite quality floor, first
  prompt/tool-budget optimization.
- Architecture: claim evidence and quality gates are persisted; profile budgets
  control tool output/report prompt/model output; source layout unchanged.
- Code/test: full suite green; Quick/Standard/Deep live pilots; quality floor
  passed after parser correction. Performance targets are **not yet met** (Quick
  77k vs 25k, Standard 147k vs 60k, Deep 283k vs 150k).
- Ops: AI-use log updated. Verdict: **APPROVE** for integration and measurement;
  performance acceptance remains open for a later round.
