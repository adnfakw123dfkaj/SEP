# Part 5 — Security and Rating Authority

**Requirements covered:** `REQ-INV-003` (Must), `REQ-SEC-001` (Must),
`REQ-INV-004` (Must)

**Owned modules:** `contracts/rating.py`, `agents/rating.py`, `security/`
(`sanitize.py`, `validate_output.py`, `security_log.py`, `redaction.py`),
`llm_clients/api_key_env.py`; plus a commit gate in `graph/trading_graph.py`
(landed via Part 1's composition root with owner review).

**Contracts used:** `RatingResult`, `RunManifest`.

**Fixtures:** `fixtures/security/injections.txt` (≥200),
`fixtures/security/benign.txt` (≥200), `fixtures/security/secrets.txt`,
`fixtures/rating/mutations/*.txt` (≥10,000 generated).

**Legend for kind:** OFFLINE / INTEGRATION / SCRIPT — see `README.md`.

---

## REQ-INV-003 — Deterministic rating authority

> The committed rating is produced only by the deterministic validator and is
> exactly one of `{Buy, Overweight, Hold, Underweight, Sell, REVIEW}`. LLM output
> is advisory. Commit requires a verified snapshot id, evidence manifest, and
> model/prompt/config versions; if any is missing the status is `REVIEW`.
> Persisted values are in the allowed set.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P5-INV003-01 | OFFLINE | Fuzz output never escapes the allowed set | `invalid_rating_escapes == 0` (10,000) |
| TC-P5-INV003-02 | OFFLINE | Committed rating is in allowed set | `committed_rating_allowed_set_rate == 1.0` |
| TC-P5-INV003-03 | OFFLINE | Missing provenance → no commit | `commit_with_missing_provenance_count == 0` |
| TC-P5-INV003-04 | OFFLINE | Adversarial text cannot flip the rating | flips `== 0` |
| TC-P5-INV003-05 | OFFLINE | Missing snapshot id → REVIEW | status == REVIEW |
| TC-P5-INV003-06 | OFFLINE | Persisted values re-validated before write | persisted out-set count == 0 |
| TC-P5-INV003-07 | OFFLINE | Idempotent commit gate (repeat commit) | one committed rating |

### TC-P5-INV003-01 — Fuzz the allowed set (negative / core)
- **Given** 10,000 mutated rating strings (including "not a Sell", "Sell-ish",
  fullwidth, markdown-bold, quoted third-party ratings).
- **When** the deterministic validator runs.
- **Then** every output is either a valid tier or `REVIEW`; none escapes.
- **Pass criterion:** `invalid_rating_escapes == 0`;
  `pytest tests/req/test_rating_invariant.py::test_fuzz --cases 10000`.
- **Traces to:** REQ-INV-003 acceptance line 1 — mandatory must-fail case.

### TC-P5-INV003-02 — Allowed set on commit (happy)
- **Given** normal decisions.
- **When** committed.
- **Then** the committed rating is one of the six values.
- **Pass criterion:** `committed_rating_allowed_set_rate == 1.0`;
  `pytest tests/req/test_rating_invariant.py::test_allowed_set`.
- **Traces to:** REQ-INV-003 acceptance line 2.

### TC-P5-INV003-03 — Provenance required (negative / bypass)
- **Given** a decision with the snapshot id, manifest, or version pin removed.
- **When** the commit gate evaluates.
- **Then** it refuses to commit and marks `REVIEW`.
- **Pass criterion:** `commit_with_missing_provenance_count == 0`;
  `pytest tests/req/test_rating_invariant.py::test_requires_provenance`.
- **Traces to:** REQ-INV-003 acceptance line 3.

### TC-P5-INV003-04 — Adversarial text (negative)
- **Given** decision text whose prose argues the opposite of its structured
  rating ("This is clearly not a Sell" while rating = Sell).
- **When** the authority resolves the committed value.
- **Then** the committed value follows the structured field, unchanged.
- **Pass criterion:** rating changes `== 0`;
  `pytest tests/req/test_rating_invariant.py::test_adversarial_text`.
- **Traces to:** REQ-INV-003 acceptance line 4.

### TC-P5-INV003-05 — Missing snapshot (negative)
- **Given** a run with no verified snapshot id.
- **When** it reaches commit.
- **Then** status is `REVIEW`, not a tier.
- **Pass criterion:** status `== REVIEW`.
- **Traces to:** REQ-INV-003 statement (commit prerequisites).

### TC-P5-INV003-06 — Persisted re-validation (state)
- **Given** a record whose stored rating was tampered out-of-set.
- **When** it is read back / written.
- **Then** the write gate re-validates and refuses an out-of-set value.
- **Pass criterion:** persisted out-of-set count `== 0`.
- **Traces to:** REQ-INV-003 statement (persisted values in the set).

### TC-P5-INV003-07 — Idempotent commit (determinism)
- **Given** a committed decision.
- **When** the commit gate is invoked again for the same decision.
- **Then** it does not create a second committed rating; the committed value is
  unique.
- **Pass criterion:** one committed rating for the decision.
- **Traces to:** REQ-INV-003 (single write entry point).

---

## REQ-SEC-001 — Untrusted input/output security

> News, social posts, and user input are sanitised before entering a prompt;
> model output is validated for structure/values before becoming state;
> suspicious or invalid content is dropped/logged and cannot affect the final
> rating; no unauthorised tool calls or role deviation.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P5-SEC001-01 | SCRIPT | Injection block/drop rate | `injection_block_or_drop_rate >= 0.99` |
| TC-P5-SEC001-02 | SCRIPT | Benign false-positive rate | `benign_false_positive_rate <= 0.05` |
| TC-P5-SEC001-03 | SCRIPT | Injected content never influences rating | `injected_influence_on_rating_count == 0` |
| TC-P5-SEC001-04 | OFFLINE | No unauthorized tool calls | `unauthorized_tool_calls == 0` |
| TC-P5-SEC001-05 | OFFLINE | Security event log coverage | `security_event_log_coverage == 1.0` |
| TC-P5-SEC001-06 | OFFLINE | Output validation rejects out-of-schema | out-of-schema reaching state == 0 |
| TC-P5-SEC001-07 | OFFLINE | Sanitizer preserves benign semantics | benign text unchanged/usable |

### TC-P5-SEC001-01 — Injection block rate (negative / core)
- **Given** `fixtures/security/injections.txt` (≥200 payloads: instruction
  override, role hijack, tool-call injection, delimiter escape).
- **When** `scripts/security_regression.py --injections 200 --assert-block-rate 0.99`.
- **Then** ≥99% are blocked or dropped.
- **Pass criterion:** `injection_block_or_drop_rate >= 0.99`.
- **Kind:** SCRIPT.
- **Traces to:** REQ-SEC-001 acceptance line 1 — mandatory must-fail case.

### TC-P5-SEC001-02 — Benign false positives (boundary ≤5%)
- **Given** `fixtures/security/benign.txt` (≥200 legitimate news/social lines).
- **When** the same script with `--benign 200 --assert-fp 0.05`.
- **Then** ≤5% are wrongly dropped.
- **Pass criterion:** `benign_false_positive_rate <= 0.05`.
- **Kind:** SCRIPT.
- **Traces to:** REQ-SEC-001 acceptance line 2.

### TC-P5-SEC001-03 — No rating influence (negative)
- **Given** an injection embedded in a fetched field.
- **When** the run completes.
- **Then** the rating equals the no-injection control run.
- **Pass criterion:** `injected_influence_on_rating_count == 0`;
  `--assert-influence 0`.
- **Kind:** SCRIPT (with recorded control).
- **Traces to:** REQ-SEC-001 acceptance line 3.

### TC-P5-SEC001-04 — No unauthorised tool calls (negative / bypass)
- **Given** model output proposing a tool the current role is not bound to.
- **When** the tool guard evaluates.
- **Then** the call is rejected and logged; execution continues without it.
- **Pass criterion:** `unauthorized_tool_calls == 0`;
  `pytest tests/security/test_prompt_injection.py::test_no_unauthorized_tool_calls`.
- **Traces to:** REQ-SEC-001 acceptance line 4.

### TC-P5-SEC001-05 — Event log coverage (state)
- **Given** each detection/sanitisation/validation event.
- **When** an event occurs.
- **Then** a `security_event` is recorded with reason.
- **Pass criterion:** `security_event_log_coverage == 1.0`;
  `pytest tests/security/test_prompt_injection.py::test_log_coverage`.
- **Traces to:** REQ-SEC-001 acceptance line 5.

### TC-P5-SEC001-06 — Output validation (negative)
- **Given** model output with an out-of-enum emotion band or missing field.
- **When** `validate_output` runs.
- **Then** it is rejected/dropped before becoming state.
- **Pass criterion:** out-of-schema reaching state `== 0`.
- **Traces to:** REQ-SEC-001 statement (validate before state).

### TC-P5-SEC001-07 — Sanitizer benign (boundary)
- **Given** benign texts with quotes, URLs, numbers.
- **When** `sanitize()` runs.
- **Then** the semantic content survives (not over-stripped).
- **Pass criterion:** benign sample passes the FP boundary (case 02) and the
  retained text still contains the key facts.
- **Traces to:** REQ-SEC-001 tradeoff (≤5% FP).

---

## REQ-INV-004 — No secret leakage

> API keys, access tokens, credentials never appear in logs, reports, manifest,
> prompts, model context, or error messages. Secrets are read only from env/key
> store and redacted before persistence.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P5-INV004-01 | OFFLINE | No secrets in artifacts | `secret_findings_in_artifacts == 0` |
| TC-P5-INV004-02 | OFFLINE | Synthetic secrets redacted | `synthetic_secret_redaction_rate == 1.0` |
| TC-P5-INV004-03 | SCRIPT | CI secret scan clean | `gitleaks` findings `== 0` |
| TC-P5-INV004-04 | OFFLINE | No secrets in model payload | `secret_occurrences_in_model_payload == 0` |
| TC-P5-INV004-05 | OFFLINE | Secret in exception text is scrubbed | 0 occurrences in raised error |
| TC-P5-INV004-06 | OFFLINE | Env-only key source | no key from file/log |

### TC-P5-INV004-01 — Artifacts clean (negative / core)
- **Given** a run with a synthetic key in the environment.
- **When** logs/reports/manifest are produced.
- **Then** none contain the key pattern.
- **Pass criterion:** `secret_findings_in_artifacts == 0`;
  `pytest tests/security/test_secret_redaction.py::test_artifacts`.
- **Traces to:** REQ-INV-004 acceptance line 1 — mandatory must-fail case.

### TC-P5-INV004-02 — Redaction rate (happy)
- **Given** `fixtures/security/secrets.txt` injected into every output sink.
- **When** redaction runs.
- **Then** 100% are redacted.
- **Pass criterion:** `synthetic_secret_redaction_rate == 1.0`;
  `pytest tests/security/test_secret_redaction.py::test_redaction`.
- **Traces to:** REQ-INV-004 acceptance line 2.

### TC-P5-INV004-03 — Secret scan (SCRIPT)
- **Given** the working tree.
- **When** `gitleaks detect --no-git --source .`.
- **Then** zero findings and exit 0.
- **Pass criterion:** `ci_secret_scan_findings == 0`.
- **Kind:** SCRIPT.
- **Traces to:** REQ-INV-004 acceptance line 3.

### TC-P5-INV004-04 — Model payload (negative)
- **Given** any prompt assembled with env keys present.
- **When** the payload is inspected before the call.
- **Then** no key appears.
- **Pass criterion:** `secret_occurrences_in_model_payload == 0`;
  `pytest tests/security/test_secret_redaction.py::test_prompt_payload`.
- **Traces to:** REQ-INV-004 acceptance line 4.

### TC-P5-INV004-05 — Exception scrubbing (negative)
- **Given** a provider error whose message contains the key (query-param auth).
- **When** it is raised/logged.
- **Then** the key is replaced with `***` and the error is otherwise intact.
- **Pass criterion:** 0 key occurrences in the raised exception.
- **Traces to:** REQ-INV-004 dependency/risk (SDK exception text) + existing
  `get_scrubbed`.

### TC-P5-INV004-06 — Env-only source (state)
- **Given** a project with no secrets on disk.
- **When** the client resolves its key.
- **Then** it reads from the env var / key store only; a key in `.env` or a file
  path is not used for these tests.
- **Pass criterion:** key provenance is environment; no file-sourced key.
- **Traces to:** REQ-INV-004 statement (env/key-store only).
