# Part 2 — Structured Debate

**Requirements covered:** `REQ-FR-003` (Must), `REQ-QUAL-001` (Must)

**Owned modules:** `contracts/debate.py`, `agents/debate/`
(`schemas.py`, `prompts.py`, `validator.py`, `convergence.py`, `quality.py`),
adapter edits to `agents/researchers/bull_researcher.py` /
`bear_researcher.py`, and `graph/conditional_logic.py` (calls
`convergence.should_stop()`).

**Contracts used:** `DebateTurn`, `EvidenceRef` (as string refs for now),
`sanitize()` (stubbed by Part 5).

**Fixtures:** `fixtures/transcripts/*.json` (golden, adversarial, 30-run
capture), `fixtures/transcripts/golden/*.json` for the quality proxies.

**Legend for kind:** OFFLINE / INTEGRATION / SCRIPT — see `README.md`.

---

## REQ-FR-003 — Structured debate protocol and convergence early-stop

> Each debate round is a structured record with at least `claim`, `stance`,
> `evidence_refs`, `assumptions`, `rebuttal_to`, `confidence`,
> `open_questions`, `requested_evidence`, `round`. The system validates fields;
> on missing/invalid it retries once, then marks `invalid` and degrades to the
> manager's free-text summary. Debate stops at max rounds or when convergence
> holds.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P2-FR003-01 | OFFLINE | Valid turns pass schema on ≥30 captured turns | `debate_turn_schema_valid_rate == 1.0` |
| TC-P2-FR003-02 | OFFLINE | Max rounds enforced exactly | `max_rounds_enforced_rate == 1.0` |
| TC-P2-FR003-03 | OFFLINE | Convergence decision correct on fixed fixtures | `early_stop_decision_correct_rate == 1.0` |
| TC-P2-FR003-04 | OFFLINE | Transcript export schema valid | `transcript_export_schema_valid_rate == 1.0` |
| TC-P2-FR003-05 | OFFLINE | Invalid turn → one retry, then `invalid` + degrade | retry count == 1, status == invalid |
| TC-P2-FR003-06 | INTEGRATION | 30 live runs produce schema-valid turns | `debate_turn_schema_valid_rate == 1.0` |

### TC-P2-FR003-01 — Schema validity (happy)
- **Given** `fixtures/transcripts/valid_30.json`: 30 recorded turns.
- **When** each is validated by `validator.validate_turn`.
- **Then** every turn passes and carries all required fields.
- **Pass criterion:** `debate_turn_schema_valid_rate == 1.0`;
  `pytest tests/req/test_debate_protocol.py::test_schema_valid --runs 30`.
- **Traces to:** REQ-FR-003 acceptance line 1.

### TC-P2-FR003-02 — Max rounds (boundary)
- **Given** a debate configured for `max_debate_rounds=2`.
- **When** the loop is driven with a fixture that never satisfies convergence.
- **Then** it stops at exactly 4 turns (2 each) and no more.
- **Pass criterion:** `max_rounds_enforced_rate == 1.0`;
  `pytest tests/req/test_debate_protocol.py::test_max_rounds`.
- **Traces to:** REQ-FR-003 acceptance line 2.

### TC-P2-FR003-03 — Convergence correctness (happy + negative)
- **Given** fixed fixtures: one pair that converges early and one that does not.
- **When** `convergence.should_stop()` evaluates each.
- **Then** the convergent fixture stops before max rounds; the non-convergent
  fixture runs to max.
- **Pass criterion:** `early_stop_decision_correct_rate == 1.0`;
  `pytest tests/req/test_debate_protocol.py::test_convergence_fixtures`.
- **Traces to:** REQ-FR-003 acceptance line 3.

### TC-P2-FR003-04 — Transcript export (state)
- **Given** a completed debate.
- **When** the JSON transcript is exported.
- **Then** every turn in the file re-validates against `DebateTurn` and the file
  has a stable schema (ordered rounds, correlation id).
- **Pass criterion:** `transcript_export_schema_valid_rate == 1.0`;
  `pytest tests/req/test_debate_protocol.py::test_export_schema`.
- **Traces to:** REQ-FR-003 acceptance line 4.

### TC-P2-FR003-05 — Retry-then-degrade (negative / bypass)
- **Given** a model output missing `evidence_refs` and `round`.
- **When** the turn is validated.
- **Then** the system retries once; if the retry is still invalid the turn is
  tagged `invalid` and the manager summary is used; the quality metric for that
  run is recorded as unavailable (not silently passed).
- **Pass criterion:** retry count == 1; turn status == `invalid`; quality metric
  flagged unavailable.
- **Traces to:** REQ-FR-003 tradeoff (retry once, degrade) — the mandatory
  must-fail case.

### TC-P2-FR003-06 — Live schema-valid rate (INTEGRATION)
- **Given** live provider and quota.
- **When** 30 real debates run.
- **Then** all turns validate.
- **Pass criterion:** `debate_turn_schema_valid_rate == 1.0` (verbatim command
  from the doc). Skipped without quota; offline case 01 covers the logic.

---

## REQ-QUAL-001 — Debate quality proxy metrics

> Every round has ≥1 `evidence_ref` or explicit `no_new_evidence`; rebuttal
> points to a valid earlier round; unsupported-claim rate ≤5%; duplicate-claim
> rate ≤10%.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P2-QUAL001-01 | OFFLINE | Evidence coverage per turn | `turns_with_evidence_or_no_new_evidence_rate == 1.0` |
| TC-P2-QUAL001-02 | OFFLINE | Rebuttal coverage | `rebuttal_coverage >= 0.90` |
| TC-P2-QUAL001-03 | OFFLINE | Unsupported-claim rate (negative) | `unsupported_claim_rate <= 0.05` |
| TC-P2-QUAL001-04 | OFFLINE | Duplicate-claim rate (negative) | `duplicate_claim_rate <= 0.10` |
| TC-P2-QUAL001-05 | OFFLINE | Quality metric computed from golden fixtures | exact expected values |
| TC-P2-QUAL001-06 | INTEGRATION | Metrics over 30 real transcripts | all four thresholds hold |

### TC-P2-QUAL001-01 — Evidence coverage (happy)
- **Given** `fixtures/transcripts/golden/*.json`.
- **When** `quality.evidence_coverage()` runs.
- **Then** every turn has `evidence_refs` non-empty or `no_new_evidence=True`.
- **Pass criterion:** rate `== 1.0`;
  `pytest tests/req/test_debate_quality.py::test_evidence_coverage --transcripts 30`.
- **Traces to:** REQ-QUAL-001 acceptance line 1.

### TC-P2-QUAL001-02 — Rebuttal coverage (boundary at 0.90)
- **Given** a golden set where 27/30 rebuttals point to a valid prior round.
- **When** `quality.rebuttal_coverage()` runs.
- **Then** 27/30 = 0.90 passes exactly; 26/30 = 0.867 fails.
- **Pass criterion:** `rebuttal_coverage >= 0.90`; test includes both the
  passing (0.90) and failing (0.867) fixture.
- **Traces to:** REQ-QUAL-001 acceptance line 2.

### TC-P2-QUAL001-03 — Unsupported-claim rate (negative)
- **Given** a transcript with 2 unsupported claims in 40 (0.05) and another with
  3 in 40 (0.075).
- **When** the metric runs.
- **Then** 0.05 passes at the boundary, 0.075 fails.
- **Pass criterion:** `unsupported_claim_rate <= 0.05`; both fixtures asserted.
- **Traces to:** REQ-QUAL-001 acceptance line 3.

### TC-P2-QUAL001-04 — Duplicate-claim rate (negative)
- **Given** a transcript with normalised duplicates: 3/30 (0.10, pass) and
  4/30 (0.133, fail).
- **When** the duplicate detector (normalised text + similarity) runs.
- **Then** the boundary case passes, the over case fails.
- **Pass criterion:** `duplicate_claim_rate <= 0.10`.
- **Traces to:** REQ-QUAL-001 acceptance line 4.

### TC-P2-QUAL001-05 — Golden determinism
- **Given** the golden fixtures with hand-computed expected metric values.
- **When** all four metrics run.
- **Then** each equals the expected value exactly (no sampling).
- **Pass criterion:** computed == expected for all four; run twice to confirm
  determinism.
- **Traces to:** REQ-QUAL-001 implementation (golden calibration).

### TC-P2-QUAL001-06 — Live metrics (INTEGRATION)
- **Given** 30 real transcripts with quota.
- **When** the four metrics run.
- **Then** all thresholds hold on live data.
- **Pass criterion:** the four `--transcripts 30` commands from the doc; skipped
  without quota.
