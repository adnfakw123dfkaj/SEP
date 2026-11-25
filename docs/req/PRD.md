# Product Requirements Document (PRD) - TradingAgents

## Document control

| Field | Value |
|---|---|
| Product | TradingAgents - auditable multi-agent trading research |
| Document type | Product Requirements Document (PRD) |
| Version | 1.0 |
| Date | 2026-11-25 |
| Team | Group 35 |
| Repository | https://github.com/adnfakw123dfkaj/SEP |
| Normative registry | `docs/req/requirements.yaml` |
| Machine schema | `docs/req/req-schema.json` |
| Related report | `Report.md` |

This PRD is the human-readable product summary for the machine-readable registry.
`requirements.yaml` remains the normative source for requirement IDs, fit
criteria, status and traceability. If this document and the registry disagree,
the registry wins.

## 1. Product purpose

TradingAgents turns a ticker and an analysis date into a research report and one
of six controlled outcomes: Buy, Overweight, Hold, Underweight, Sell, or REVIEW.
The product is advisory only. It does not place orders.

The product exists to demonstrate that a multi-agent LLM system can be:

- bounded by explicit profiles and token budgets;
- auditable through evidence references, a run manifest and a committed rating;
- resilient when vendors or models fail;
- safe when untrusted text enters the pipeline;
- honest when data is unavailable or a run cannot complete.

## 2. Users and use cases

| User | Need | Product response |
|---|---|---|
| Researcher | Compare a ticker on a historical date | CLI run with date-pinned data and a report |
| Reviewer | Check why a rating was produced | Manifest, evidence index, claim index and rating authority |
| Operator | Control cost and latency | Quick / Standard / Deep profiles and hard budget caps |
| Course assessor | Verify process and governance | Requirements, ADRs, trace matrix, gate evidence and transcripts |

Primary use case: a user runs the CLI for one ticker and one date, receives a
report, and can inspect every exact number and the final committed rating.

## 3. Scope

### In scope

- Multi-agent analysis: market, sentiment, news and fundamentals.
- Bounded research and risk debate.
- Trader plan and Portfolio Manager decision.
- Deterministic rating authority.
- Evidence references, claim groups and per-run manifest.
- Point-in-time data filtering and graceful degradation.
- Token/cost accounting and profile-level budget enforcement.
- Offline verification and blocking Git/CI gates.

### Out of scope

- Order execution or brokerage integration.
- A web UI or multi-user service.
- Investment advice or portfolio custody.
- A human support queue for ambiguous requests.
- A general-purpose intent classifier.

## 4. Product goals and success measures

| Goal | Measure | Target |
|---|---|---|
| Bounded operation | Hard token cap enforcement | No run crosses its profile cap |
| Quality | Quality floor with evidence and contradiction checks | Pass before a normal rating is committed |
| Auditability | Manifest, evidence index and claim index | Present for every completed run |
| Safety | Invalid rating, unauthorised tool or leaked secret | Fail closed / record event |
| Resilience | Source failure or model failure | Fallback or REVIEW, never fabricated data |
| Reproducibility | Offline deterministic suite | Green in CI |

## 5. Functional and quality requirements

The table below summarises the 14 accepted top-level requirements. The
`Fit criterion` column gives the primary machine-checkable acceptance measure;
the full list of metrics and verification commands is in `requirements.yaml`.

| ID | Type | Priority | Status | Requirement | Fit criterion |
|---|---|---|---|---|---|
| REQ-FR-001 | functional | must | implemented | Provide Quick, Standard and Deep profiles with fixed analyst sets, rounds, model routes, budgets, timeouts and cache TTLs; record the profile and overrides in the manifest. | Profile matrix match rate = 1.0; manifest profile coverage = 1.0 |
| REQ-FR-002 | functional | should | implemented | Preflight the ticker and price availability before the graph; invalid input stops with no analyst calls and no LLM tokens. | Analyst calls on invalid input = 0; preflight failure tokens = 0 |
| REQ-FR-003 | functional | must | implemented | Use a typed debate turn with claim, stance, evidence refs, assumptions, rebuttal, confidence, open questions and round; validate, retry once, then degrade; stop at max rounds or convergence. | Debate turn schema validity = 1.0; max rounds enforced = 1.0 |
| REQ-QUAL-001 | quality | must | implemented | Enforce debate-quality proxies: evidence or explicit no-new-evidence; valid rebuttal; low unsupported and duplicate claim rates. | Evidence coverage = 1.0; rebuttal coverage >= 0.90; unsupported <= 0.05 |
| REQ-FR-004 | functional | must | implemented | Attach evidence refs to substantive claims and write a run manifest with profile, models, vendors, tokens, cost, fallback/security events, rating and status. | Numeric claims with refs = 1.0; manifest schema validity = 1.0 |
| REQ-QUAL-002 | quality | should | implemented | Keep report numbers consistent with the verified snapshot; citation support must be high and claim evidence must be present. | Numeric contradiction rate <= 0.02; citation support >= 0.95 |
| REQ-INV-001 | invariant | should | implemented | Write decision records atomically and idempotently; a rerun with the same key must not add a duplicate decision. | Partial records = 0; duplicate entries = 0 |
| REQ-FR-005 | functional | must | implemented | Use checkpoints, TTL caches and bounded fallback; never fabricate data when a source is unavailable. | Resume reuse >= 0.90; no duplicate completed-node calls; no stale cache use |
| REQ-INV-002 | invariant | should | implemented | Enforce point-in-time data: no future data for prices, indicators, news, fundamentals, macro, insider or social sources. | PIT test coverage = 100%; no future-dated value is used |
| REQ-INV-003 | invariant | must | implemented | Commit only an allowed rating; missing or invalid provenance becomes REVIEW; agents remain advisory. | Adversarial rating attempts cannot flip the committed rating |
| REQ-SEC-001 | security | must | implemented | Sanitise untrusted input, validate model output, reject role-unauthorised tools and record security events. | Injection block rate >= 0.99; unauthorised tool executions = 0 |
| REQ-INV-004 | invariant | must | implemented | Keep secrets out of logs, prompts, manifests, reports and exceptions. | Redaction test rate = 1.0; provider keys are read from environment only |
| REQ-PER-001 | performance | must | implemented | Keep tiered latency observable and within profile expectations. | Profile latency benchmarks are recorded and compared |
| REQ-COST-001 | cost | must | partial | Enforce per-profile token budgets, pre-call hard stops, cost reporting and compaction/routing limits. | No run crosses its cap; cost report is present; aggregate p95 still open |

`REQ-COST-001` is intentionally marked `partial`: the hard stop and cost report
are implemented, while progressive routing and aggregate p95 acceptance are not
fully closed.

## 6. Non-functional constraints

- **Point-in-time:** historical runs must not use information published after the
  analysis date.
- **Determinism at the boundary:** the LLM output may vary, but the committed
  rating and the write path must not.
- **Fail closed:** missing provenance, invalid output, budget overflow or an
  unauthorised tool must produce REVIEW or a recorded rejection, not silent
  success.
- **Cost control:** Quick, Standard and Deep use hard caps of 80k, 150k and 300k
  tokens respectively.
- **Auditability:** every completed run must leave a report, manifest, evidence
  index and claim index.
- **Security:** untrusted text never becomes state without sanitisation and output
  validation.
- **Portability:** the CLI must run on Windows and Linux; tests separate offline
  deterministic cases from live provider cases.

## 7. Assumptions

- A user provides a valid ticker and a date.
- Provider API keys are available for live runs; offline runs do not need keys.
- Vendor data can be missing, delayed or partial; the product must degrade rather
  than fabricate.
- A human owns live runs, approvals and merges.

## 8. Acceptance and release criteria

A release is acceptable when:

1. The offline suite passes for the changed scope.
2. The blocking gate configuration is present for a PR to `master`.
3. A normal run produces a report, manifest, evidence index and claim index.
4. The quality floor passes before a normal rating is committed.
5. The final rating is one of the allowed values, or REVIEW with a reason.
6. Known gaps are recorded as `partial`, not described as complete.

## 9. Discarded and source-only requirements

The two `-other` entries below are **not accepted product requirements**. They
remain in the YAML `discarded:` section for decision traceability.

| ID | Source | Original idea | Status | Reason |
|---|---|---|---|---|
| REQ-FR-01-other | other-doc | Full intent classification for off-topic or ambiguous requests | Discarded from accepted scope; replaced by REQ-FR-002 | An extra LLM/classifier adds latency and cost; the ticker/data preflight covers the critical validity check |
| REQ-FR-03-other | other-doc | Ambiguous-request clarification and a human handling path | Discarded | Requires UI, queue and human SLA work outside the course cycle |

Both are explicitly excluded from the 14 accepted requirements. They are not
missing implementation of an accepted requirement.

## 10. Traceability

| Requirement area | Primary implementation | Verification | Runtime evidence |
|---|---|---|---|
| Profiles and preflight | `tradingagents/profiles.py`, `preflight.py` | `tests/req/test_profiles.py`, `test_preflight.py` | Manifest profile, preflight result |
| Debate and quality | `agents/debate/`, `graph/conditional_logic.py` | `test_debate_protocol.py`, `test_debate_quality.py` | Debate transcript, quality metrics |
| Evidence and claims | `evidence/`, `reporting.py`, manifest writer | `test_evidence_manifest.py`, `test_claims.py` | Evidence Index, Claim Index, manifest |
| Resilience and PIT | `cache/`, `graph/checkpointer.py`, vendor date filters | `test_cache.py`, `test_checkpoint_resume.py`, `test_point_in_time.py` | Cache metrics, fallback events, `pit_coverage` |
| Rating authority | `rating_authority.py`, composition root | `test_rating_invariant.py` | Committed rating, `rating_authority` |
| Security | `security/` and graph dispatch | `tests/security/` | `security_events` |
| Cost and quality | `cost/`, `GuardedLLM`, quality floor | `test_token_cost.py`, `test_budget.py` | Cost report, `budget_exceeded`, quality floor |

## 11. Open items and change policy

| Item | Current state | Next step |
|---|---|---|
| Aggregate p95 cost | `REQ-COST-001` partial | Measure across a stable profile matrix before claiming acceptance |
| Progressive context routing | Implemented in cost layer, not fully wired | Wire summarisation/cheaper-model routing with protected evidence keys |
| Safety-path review | Human process and ADR obligation | Add a path-specific review rule if the platform policy requires it |
| D8 source layout | Compatibility entry points | Physical migration remains a future option, not a silent claim |

Changes to accepted requirements, safety boundaries or test obligations require a
new approval record and, where structural, an ADR. Silent weakening of a fit
criterion is not permitted.
