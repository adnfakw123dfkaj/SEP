# Part 5 — Requirement → implementation → test traceability

Owner: 陈妍妍. Branch: `part-5/security-rating`.
Test-approval: `docs/approvals/chg-2026-11-18-part5-security-rating.json`
(approved 2026-11-18T06:43:59+00:00, before implementation).

## REQ-INV-003 — Deterministic rating authority

| Case | Implementation | Test |
|---|---|---|
| INV003-01 fuzz 10k | `rating_authority.resolve_rating` + `commit_rating` (allowed-set check) | `test_rating_invariant.py::test_fuzz` |
| INV003-02 allowed set on commit | `contracts/rating.RatingResult`, `commit_rating` | `::test_allowed_set` |
| INV003-03 provenance required | `rating_authority.validate_provenance` | `::test_requires_provenance`, `::test_requires_provenance_rejects_free_text_source` |
| INV003-04 adversarial text | `_candidate_to_rating` (structured/parse), shared parser | `::test_adversarial_text_cannot_flip` |
| INV003-05 missing snapshot | `validate_provenance` (missing + unverified) | `::test_missing_snapshot_review` |
| INV003-06 persisted revalidation | write gate + `read_committed_rating` | `::test_persisted_revalidation` |
| INV003-07 idempotent commit | `commit_rating` per `decision_id` | `::test_idempotent_commit` |

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
  documented in `docs/part5-integration.md` but **not** performed (out of scope
  for this Part / requires owner review).
- **Concurrency:** only serial idempotency is implemented/tested. Atomic
  concurrent commit is delegated to the Part 3 store contract (documented), not
  verified here.
- Integration-marked live cases (none remain in Part 5 after moving the rate
  tests offline). Results are for fixed fixtures, not a live model.
