# Part 5 — Requirement → implementation → test traceability

Owner: 陈妍妍. Branch: `part-5/security-rating`. Final commit: `6bcd61e`.
Test-approvals (all preserved): `chg-2026-11-18-part5-security-rating`,
`chg-2026-11-18-part5-acceptance-2`, `chg-2026-11-18-part5-rating-failclosed`.
G1 multi-round limitation: `docs/approvals/part5-g1-multiround-limitation.md`.

## REQ-INV-003 — Deterministic rating authority

| Case | Implementation | Test |
|---|---|---|
| INV003-01 fuzz 10k | `rating_authority.resolve_rating` + `commit_rating` (allowed-set check) | `test_rating_invariant.py::test_fuzz` |
| INV003-02 allowed set on commit | `contracts/rating.RatingResult`, `commit_rating` | `::test_allowed_set` |
| INV003-03 provenance required | `rating_authority.validate_provenance` | `::test_requires_provenance`, `::test_requires_provenance_rejects_free_text_source` |
| INV003-04 adversarial text | `_candidate_to_rating` (structured/parse), shared parser | `::test_adversarial_text_cannot_flip` |
| INV003-05 missing snapshot | `validate_provenance` (missing + unverified) | `::test_missing_snapshot_review` |
| INV003-06 persisted revalidation (fail closed) | `_classify_existing` + `read_committed_rating`; corrupt -> REVIEW/non-tradeable | `::test_persisted_revalidation`, `::test_corrupt_record_is_classified_accurately`, `::test_corrupt_source_eventually_rejected_on_retry_and_readback`, `::test_decision_id_mismatch_is_rejected` |
| INV003-07 idempotent commit (request-validated) | `commit_rating` validates request provenance before idempotency/conflict; returns persisted source | `::test_idempotent_commit`, `::test_retry_returns_persisted_source`, `::test_unverified_same_source_retry_is_rejected`, `::test_valid_commit_and_valid_retry_still_work` |

Preserved parser API: `agents/rating.py` `extract_rating/parse_rating/run_rating`
unchanged; authority reuses `extract_rating`.

## REQ-SEC-001 — Untrusted input/output

| Case | Implementation | Test |
|---|---|---|
| SEC001-01 injection block ≥0.99 | `security/sanitize.py` | `test_prompt_injection.py::test_injection_block_rate`; `scripts/security_regression.py --injections 200 --assert-block-rate 0.99` |
| SEC001-02 benign FP ≤0.05 | `sanitize` | `::test_benign_false_positive_rate`; script `--benign 200 --assert-fp 0.05` |
| SEC001-03 no rating influence | `sanitize` + `commit_rating` control | `::test_injected_content_does_not_change_rating`; script `--assert-influence 0` |
| SEC001-04 no unauthorised tool calls | `security/tool_guard.py` (reject before execute) | `::test_no_unauthorized_tool_calls` |
| SEC001-05 event log coverage | `security/security_log.py` | `::test_log_coverage`, `::test_log_is_redacted` |
| SEC001-06 output validation | `security/validate_output.py` | `::test_output_validation` |
| SEC001-07 benign semantics | `sanitize` (facts preserved) | `::test_sanitizer_preserves_benign_semantics` |

Negative controls proving the tests can fail:
`::test_sanitizer_detects_known_injection_by_construction`,
`::test_influence_detector_would_catch_an_actual_flip`.

## REQ-INV-004 — No secret leakage

| Case | Implementation | Test |
|---|---|---|
| INV004-01 artifacts clean | `security/redaction.py` (`scrub_manifest`, `RedactingFilter`) | `test_secret_redaction.py::test_artifacts` |
| INV004-02 redaction rate 1.0 | `redact` / `redact_obj` / `redact_text` | `::test_redaction` |
| INV004-03 gitleaks clean | `gitleaks detect --no-git --source .` | external (NOT in CI) |
| INV004-04 model payload | `safe_prompt_payload` | `::test_prompt_payload` |
| INV004-05 exception scrub | `redact_obj` (exception branch); existing `get_scrubbed` | `::test_redaction`, `::test_existing_scrub_redacts_secret` |
| INV004-06 env-only source | redaction reads canonical env; client chain unchanged | `::test_env_only_key_source` |

## Commands

```bash
cd tradingagents
python -m pytest tests/req/test_rating_invariant.py tests/security -q
python -m pytest tests/test_rating_integrity.py tests/test_post_screen.py \
                 tests/test_api_key_env.py -q
# repo root:
python scripts/security_regression.py --all
python scripts/generate_security_fixtures.py   # regenerate fixtures (deterministic)
```

## Unverified / not done

- **No gitleaks step exists in any workflow** (`.github/workflows/*`): INV004-03
  is not run in CI and this change does not modify shared CI.
  - **Repo-level scan** (`gitleaks detect --no-git --source .`): **2 findings**,
    both in pre-existing test files this change did not touch —
    `tradingagents/tests/test_alpha_vantage_hardening.py:165` and
    `tradingagents/tests/test_fred.py:261`.
  - **This change's new files**: **0 findings**.
  - **Triage of the two existing findings:** both are **synthetic test keys**
    (false positives), not real credentials:
    - `test_alpha_vantage_hardening.py:165` — `AVKEY1234567890XYZ`, a fake Alpha
      Vantage key used to assert the key is scrubbed from HTTP errors.
    - `test_fred.py:261` — `abcdef0123456789abcdef0123456789`, a fake 64-hex
      FRED-style key used to assert the key is kept out of errors.
    - Rule: `generic-api-key`. Judgement: test data in test files; the repo's G2
      static check already skips `tests/`. Not suppressed/expanded here; the
      "0 findings" requirement is **not** met at repo level, independently of
      this change.
- **pyright excludes `tradingagents/`** (`pyrightconfig.json`), so the new Part 5
  modules are not type-checked by CI. Run explicitly in isolation, pyright on the
  new modules reported 0 errors (supplementary, not CI-enforced).
- Wiring into `graph/trading_graph.py`, analysts, and Part 3 records/manifest is
  documented in `docs/intermediate-artifacts/part5-integration.md` but **not** performed (out of scope
  for this Part / requires owner review).
- **Concurrency:** only serial idempotency is implemented/tested. Atomic
  concurrent commit is delegated to the Part 3 store contract (documented), not
  verified here.
- Integration-marked live cases (none remain in Part 5 after moving the rate
  tests offline). Results are for fixed fixtures, not a live model.

## Part 1 / Part 3 integration handoff (not yet performed)

Detailed call sites and verification scenarios are in
`docs/intermediate-artifacts/part5-integration.md`.

- **Part 1** (`graph/trading_graph.py::record_decision` and boundaries): build
  verified `Provenance` (set `snapshot_verified=True` only after real
  verification); call `commit_rating(...)` with a stable `decision_id`; use
  `sanitize` on fetched fields; `safe_prompt_payload` before model calls;
  `ToolGuard` on dispatch; `install_log_filter`/`register_handler` on handlers;
  `drain_events` into the manifest.
- **Part 3** (records/manifest): implement `Store.read/write` (atomic per id),
  persist the full record **including `snapshot_verified`**, `scrub_manifest`
  before writing artifacts, include `security_events` and the final
  rating/reason_codes/provenance.

Verification scenarios expected from those integrations are listed per item in
`docs/intermediate-artifacts/part5-integration.md` (unverified snapshot -> REVIEW; injected field does
not change rating; unbound tool 0 executions; key never in output; tampered
record reads as REVIEW; manifest replays to same rating).

## G2 static analysis — correct interpretation

`check_static_analysis.py` treats `dependencies` as an **ALWAYS_ON** check
(alongside `lint`, `type_check`), so `dependencies=false` is **not** informational
— it is a real G2 failure. Only `pip-audit` is informational.

`check_dependencies()` is a single `import tradingagents` and returns False on any
import error. The correct way to run/assess it is the CI path
(`.github/workflows/gates.yml` gate-static-analysis): it runs
`pip install -e tradingagents` **before** running all checks.

- **Cause of an earlier `dependencies: false`:** it was observed by running
  `python3 scripts/gates/run_static_checks.py` with the **system Python, without
  the editable install**, and with `sys.path[0]=scripts/gates` — so
  `import tradingagents` raised `ModuleNotFoundError`. That is a **local
  environment artifact, not a dependency or code defect.** (A related reporting
  error: that run's real exit code is **1**, but it was misreported as 0 because
  the command was piped through `tail`, whose exit code was shown instead.)
- **Correct result (editable-installed env, as in CI):**
  `{"contract": true, "security": true, "api_surface": true, "permission": true,
  "dependencies": true}` and `run_static_checks.py` exits **0**.
- **G2 evaluator (real results + CI-computed lint/type_check):**
  `lint=true`, `type_check=true`, `dependencies=true`, contract/security/
  api_surface/permission=true → **G2 status: pass.** The gate is evaluated
  separately from the script exit code; script exit 0 is not equated with G2
  passing.
- No gate was modified. There is **no dependency-related G2 todo**; G2 passes
  when run in the installed environment. `pip-audit` (informational only) is not
  a blocker.
