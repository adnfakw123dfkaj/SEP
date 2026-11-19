# Part 3 — Evidence Chain, Report, and Records

**Requirements covered:** `REQ-FR-004` (Must), `REQ-QUAL-002` (Should),
`REQ-INV-001` (Should)

**Owned modules:** `contracts/manifest.py`, `contracts/evidence.py`,
`evidence/` (reference registry, `fidelity.py`), `records/`, `reporting.py`.

**Contracts used:** `RunManifest`, `EvidenceRef`; reads `RatingResult` (Part 5)
and `LLMCallEvent` (Part 6), `ProfileConfig` (Part 1).

**Fixtures:** `fixtures/reports/*.md`, `fixtures/manifests/*.json`,
`fixtures/llm_events/*.jsonl`, `fixtures/reports/numeric_cases/*.json`.

**Legend for kind:** OFFLINE / INTEGRATION / SCRIPT — see `README.md`.

---

## REQ-FR-004 — Evidence-chain report and run manifest

> Every substantive fact/number in the report carries an `evidence_ref`. Each run
> writes `manifest.json` with run_id, ticker, date, profile, analysts, models,
> provider, prompt/config version, vendor versions, cache hits, per-agent token
> usage, cost estimate, fallback/security events, final rating, timestamps,
> status.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P3-FR004-01 | OFFLINE | Numeric claims carry evidence refs | `numeric_claims_with_evidence_ref_rate == 1.0` |
| TC-P3-FR004-02 | OFFLINE | Qualitative claims mostly carry refs | `qualitative_claims_with_evidence_ref_rate >= 0.95` |
| TC-P3-FR004-03 | OFFLINE | Manifest validates against schema | `manifest_schema_valid_rate == 1.0` |
| TC-P3-FR004-04 | OFFLINE | Manifest token sum matches LLM events | `manifest_token_sum_relative_error <= 0.05` |
| TC-P3-FR004-05 | OFFLINE | Manifest replays to the same rating | `manifest_replay_success_rate == 1.0` |
| TC-P3-FR004-06 | OFFLINE | Missing evidence_ref on a number → flagged/blocked (negative) | unsupported flag set |

### TC-P3-FR004-01 — Numeric refs (happy + negative)
- **Given** `fixtures/reports/numeric_cases/`: reports where every number has a
  ref, and one where a number ("RSI 71.3") has no ref.
- **When** the reference checker runs.
- **Then** the fully-referenced report passes at 1.0; the one with an orphan
  number is flagged (or blocked) and the run is not marked fully valid.
- **Pass criterion:** `numeric_claims_with_evidence_ref_rate == 1.0` for the
  clean set; the orphan case yields an `unsupported` marker;
  `pytest tests/req/test_evidence_manifest.py::test_numeric_refs --reports 30`.
- **Traces to:** REQ-FR-004 acceptance line 1.

### TC-P3-FR004-02 — Qualitative refs (boundary 0.95)
- **Given** reports at 0.95 and 0.93 qualitative-ref coverage.
- **When** the checker runs.
- **Then** 0.95 passes, 0.93 fails.
- **Pass criterion:** `qualitative_claims_with_evidence_ref_rate >= 0.95`.
- **Traces to:** REQ-FR-004 acceptance line 2.

### TC-P3-FR004-03 — Manifest schema (happy + negative)
- **Given** `fixtures/manifests/valid/*.json` and `invalid/` (missing `run_id`,
  wrong timestamp type, unknown status).
- **When** validated against the `RunManifest` schema.
- **Then** all valid pass; every invalid is rejected with the offending field
  named.
- **Pass criterion:** `manifest_schema_valid_rate == 1.0` on valid;
  `pytest tests/req/test_evidence_manifest.py::test_manifest_schema --runs 30`.
- **Traces to:** REQ-FR-004 acceptance line 3.

### TC-P3-FR004-04 — Token sum (boundary error ≤5%)
- **Given** a manifest and its `LLMCallEvent` stream where per-agent sums differ
  by 3% (pass) and 8% (fail).
- **When** the checker compares manifest `token_usage_by_agent` to the events.
- **Then** 3% passes, 8% fails.
- **Pass criterion:** `manifest_token_sum_relative_error <= 0.05`.
- **Traces to:** REQ-FR-004 acceptance line 4.

### TC-P3-FR004-05 — Replay (state + determinism)
- **Given** a committed manifest + recorded inputs.
- **When** replayed against recorded data versions.
- **Then** it reproduces the same final rating and the same evidence ids.
- **Pass criterion:** `manifest_replay_success_rate == 1.0`;
  `pytest tests/req/test_evidence_manifest.py::test_replay`.
- **Traces to:** REQ-FR-004 acceptance line 5.

### TC-P3-FR004-06 — Orphan number must-fail (negative / bypass)
- **Given** a report with one numeric claim lacking a ref.
- **When** the run finalises.
- **Then** the claim is marked `unsupported` and the report does not claim full
  numeric-ref coverage; if strict mode, finalisation blocks.
- **Pass criterion:** orphan gets `unsupported`; strict mode raises.
- **Traces to:** REQ-FR-004 tradeoff (substantive-claim unit) — mandatory
  must-fail case.

---

## REQ-QUAL-002 — Report numeric faithfulness and citation support

> Numeric claims agree with the verified market snapshot; ≥95% of citations
> point to real sources; unsupported-claim rate ≤5%; report passes schema; the
> numeric extractor has recall ≥95%.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P3-QUAL002-01 | OFFLINE | Contradiction rate vs snapshot | `numeric_claim_contradiction_rate <= 0.02` |
| TC-P3-QUAL002-02 | OFFLINE | Citation support | `citation_support_rate >= 0.95` |
| TC-P3-QUAL002-03 | OFFLINE | Unsupported-claim rate | `unsupported_claim_rate <= 0.05` |
| TC-P3-QUAL002-04 | OFFLINE | Report schema valid | `report_schema_valid_rate == 1.0` |
| TC-P3-QUAL002-05 | OFFLINE | Extractor recall on golden numerics | `numeric_claim_detection_recall >= 0.95` |
| TC-P3-QUAL002-06 | OFFLINE | Snapshot contradiction caught (negative) | flagged contradiction |

### TC-P3-QUAL002-01 — Contradiction (negative + boundary)
- **Given** reports where numbers match the snapshot, and one where "close 189.5"
  contradicts snapshot close 187.2.
- **When** `fidelity` compares extracted numbers to the verified snapshot.
- **Then** the clean report passes (0% contradiction ≤2%); the contradicting
  one is flagged.
- **Pass criterion:** `numeric_claim_contradiction_rate <= 0.02`;
  `pytest tests/req/test_report_faithfulness.py::test_numeric --reports 30`.
- **Traces to:** REQ-QUAL-002 acceptance line 1.

### TC-P3-QUAL002-02 — Citation support (boundary 0.95)
- **Given** citation sets at 0.96 and 0.94 support.
- **When** checked against real source ids.
- **Then** 0.96 passes, 0.94 fails.
- **Pass criterion:** `citation_support_rate >= 0.95`.
- **Traces to:** REQ-QUAL-002 acceptance line 2.

### TC-P3-QUAL002-03 — Unsupported (boundary 0.05)
- **Given** 5/100 (0.05 pass) and 6/100 (0.06 fail).
- **Pass criterion:** `unsupported_claim_rate <= 0.05`.
- **Traces to:** REQ-QUAL-002 acceptance line 3.

### TC-P3-QUAL002-04 — Report schema (negative)
- **Given** one well-formed and one malformed report (missing required section).
- **Then** schema-valid rate 1.0 on the valid set; malformed rejected.
- **Pass criterion:** `report_schema_valid_rate == 1.0`.
- **Traces to:** REQ-QUAL-002 acceptance line 4.

### TC-P3-QUAL002-05 — Extractor recall (boundary 0.95)
- **Given** golden fixtures with hand-labelled numeric claims (e.g. 40 numbers).
- **When** the extractor runs.
- **Then** it detects ≥38/40 (0.95).
- **Pass criterion:** `numeric_claim_detection_recall >= 0.95`;
  `pytest tests/req/test_report_faithfulness.py::test_extractor_recall`.
- **Traces to:** REQ-QUAL-002 acceptance line 5 + tradeoff (recall guard against
  false-pass).

### TC-P3-QUAL002-06 — Snapshot contradiction must-fail (negative)
- **Given** a claim "support bounced at 150" but snapshot never touched 150.
- **When** fidelity runs.
- **Then** it is flagged as a contradiction against the snapshot.
- **Pass criterion:** contradiction flagged; mandatory must-fail case.
- **Traces to:** REQ-QUAL-002 statement (numbers agree with snapshot).

---

## REQ-INV-001 — Atomic and idempotent decision record

> The decision record (state JSON + report tree + manifest) is written as one
> atomic unit; an interrupted write leaves the previous complete record or the
> new complete one, never partial. Re-running the same `(ticker, trade_date,
> run_signature)` must not append a second decision entry.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P3-INV001-01 | OFFLINE | Fault injection leaves no partial record | partial records `== 0` (100 trials) |
| TC-P3-INV001-02 | OFFLINE | Idempotent append for same key | log entries `== 1` after N runs |
| TC-P3-INV001-03 | OFFLINE | Different signature → independent versions | distinct versions; latest projection unique |
| TC-P3-INV001-04 | OFFLINE | Record completeness hash verifies | hash pass rate `== 1.0` |
| TC-P3-INV001-05 | OFFLINE | Crash between files leaves prior record intact | prior record intact, parseable |
| TC-P3-INV001-06 | OFFLINE | Concurrent writers do not interleave | one complete record wins |

### TC-P3-INV001-01 — Fault injection (negative / boundary)
- **Given** staging-dir + atomic-rename writer.
- **When** the process is killed at randomised points during the write, 100 times.
- **Then** every surviving record parses completely; a reader sees old or new,
  never partial.
- **Pass criterion:** partial records `== 0`;
  `pytest tests/req/test_records.py::test_fault_injection`.
- **Traces to:** REQ-INV-001 acceptance line 1.

### TC-P3-INV001-02 — Idempotent append (determinism)
- **Given** the same `(ticker, trade_date, run_signature)`.
- **When** the decision is stored N times.
- **Then** the memory log has exactly one entry for the key.
- **Pass criterion:** log entries `== 1`;
  `pytest tests/req/test_records.py::test_idempotent_append`.
- **Traces to:** REQ-INV-001 acceptance line 2.

### TC-P3-INV001-03 — Signature versions (state)
- **Given** two runs with different `run_signature` (e.g. different profile).
- **When** both are stored.
- **Then** they occupy distinct versions and the "latest decision" projection is
  unique and deterministic.
- **Pass criterion:** distinct record ids; projection resolves to exactly one;
  `pytest tests/req/test_records.py::test_signature_versions`.
- **Traces to:** REQ-INV-001 acceptance line 3.

### TC-P3-INV001-04 — Record hash (state)
- **Given** a completed record set.
- **When** the completeness hash is recomputed.
- **Then** it matches the stored hash; a tampered byte fails verification.
- **Pass criterion:** hash pass rate `== 1.0` on clean, fail on tampered;
  `pytest tests/req/test_records.py::test_record_hash`.
- **Traces to:** REQ-INV-001 acceptance line 4.

### TC-P3-INV001-05 — Crash between files (negative)
- **Given** the writer writes state JSON, then report tree, then manifest.
- **When** the process dies after the first file but before the second.
- **Then** the staging directory is discarded on next start and the previous
  complete record (if any) remains intact.
- **Pass criterion:** no partial record readable; prior record intact.
- **Traces to:** REQ-INV-001 statement (whole set is atomic).

### TC-P3-INV001-06 — Concurrent writers (race)
- **Given** two processes writing the same `(ticker, trade_date)` with the same
  signature at once.
- **When** both attempt the atomic rename.
- **Then** exactly one complete record wins; neither leaves a partial file.
- **Pass criterion:** one complete record; the other's staging is discarded.
- **Traces to:** REQ-INV-001 atomicity under concurrency.
