# Part 5 — Test approval list (G1)

**Change id:** `chg-2026-11-18-part5-security-rating`
**Approved by:** 陈妍妍 (Chen Yanyan)
**Approved at:** 2026-11-18T06:43:59+00:00 (UTC; recorded before implementation)
**Covered test files (G1 `tests`):**
- `tradingagents/tests/req/test_rating_invariant.py`
- `tradingagents/tests/security/test_prompt_injection.py`
- `tradingagents/tests/security/test_secret_redaction.py`
- `tradingagents/tests/fixtures/security/injections.txt` (test fixture)
- `tradingagents/tests/fixtures/security/benign.txt` (test fixture)
- `tradingagents/tests/fixtures/security/secrets.txt` (test fixture)

This list describes the scenarios the approved tests assert. Function names and
node ids already on `master` are preserved (only their bodies change from a
module-existence placeholder to a real behavioural assertion). New scenarios that
are substantially added after this approval are **not** silently treated as
approved; if a new *file* must be approved, a separate approval record is added.

## Baseline at approval time (Python 3.14, isolated venv)

Command:
```
cd tradingagents
python -m pytest tests/req/test_rating_invariant.py tests/security -q
```
Result: **7 passed, 10 skipped, 2 deselected**. Full suite:
**1432 passed, 56 skipped, 13 deselected**.

Skips are the `require("tradingagents.security")` / `require("tradingagents.records")`
/ `require("tradingagents.security.redaction")` placeholders these tests replace.

## REQ-INV-003 — `tests/req/test_rating_invariant.py`

| node id | scenario | expected assertion |
|---|---|---|
| `test_allowed_set` | happy: normal decisions through the authority | committed rating ∈ {Buy,Overweight,Hold,Underweight,Sell,REVIEW}; `committed_rating_allowed_set_rate == 1.0` |
| `test_fuzz` | negative: ≥10,000 seeded mutations (fullwidth, markdown-bold, "not a Sell", "Sell-ish", quotes) | every committed/resolved value ∈ allowed set; `invalid_rating_escapes == 0` |
| `test_adversarial_text_cannot_flip` | negative: prose argues opposite of structured field | committed value follows structure; `rating_change_count == 0` |
| `test_review_sentinel` | no readable rating | `REVIEW`, never a guessed tier |
| `test_run_rating_prefers_structured_field` | structured `final_rating` over text | structured value wins |
| `test_fullwidth_and_markdown_tolerant` | fullwidth colon / bold | parsed correctly |
| `test_requires_provenance` | negative: snapshot/manifest/version removed | refused, `REVIEW`, reason code present; `commit_with_missing_provenance_count == 0` |
| `test_missing_snapshot_review` | negative: no verified snapshot id | status `REVIEW` |
| `test_persisted_revalidation` | state: out-of-set stored value | write adapter rejects; `persisted_out_of_set_count == 0` (uses Part 5 store adapter + in-memory double, not `tradingagents.records`) |
| `test_idempotent_commit` | determinism: repeat commit, stable decision id | exactly one committed rating; distinct ids do not collide |

## REQ-SEC-001 — `tests/security/test_prompt_injection.py`

| node id | scenario | expected assertion |
|---|---|---|
| `test_no_unauthorized_tool_calls` | negative: role proposes unbound tool | guard rejects before execution; `executions == 0`; event logged; subsequent authorised call still runs |
| `test_log_coverage` | state: each detect/sanitise/validate/tool-reject event | `SecurityEvent` recorded with reason; `security_event_log_coverage == 1.0`; entries redacted |
| `test_output_validation` | negative: out-of-enum / missing field | rejected before state; `out_of_schema_reaching_state == 0` |
| `test_injection_block_rate` | injection fixtures (≥200 distinct payloads) | `injection_block_or_drop_rate >= 0.99` (offline, deterministic; marker adjusted to offline rules test) |
| `test_benign_false_positive_rate` | benign fixtures (≥200 distinct lines) | `benign_false_positive_rate <= 0.05`; key facts (numbers, URLs) retained |

Note: `test_injection_block_rate` / `test_benign_false_positive_rate` are currently
marked `integration`; because they become pure offline rule tests they are moved
to the default (non-`integration`) run so the default suite covers them.

## REQ-INV-004 — `tests/security/test_secret_redaction.py`

| node id | scenario | expected assertion |
|---|---|---|
| `test_existing_scrub_redacts_secret` | existing `get_scrubbed` | key replaced with `***` (kept as-is) |
| `test_artifacts` | negative: synthetic key in env → logs/reports/manifest | `secret_findings_in_artifacts == 0` |
| `test_redaction` | happy: synthetic secrets in nested structures/logs/exceptions | `synthetic_secret_redaction_rate == 1.0` |
| `test_prompt_payload` | negative: key present, payload inspected pre-call | `secret_occurrences_in_model_payload == 0` |

Additional INV004 scenarios (`test_processor_secret_in_exception`, env-only key
source) are added within this same file only if approved; otherwise they are
reported as new and not counted as approved.
