# Part 5 — Integration & handoff (security & rating authority)

This describes how the Part 5 modules plug into the composition root (Part 1) and
the records/manifest layer (Part 3). **Part 5 does not modify those modules in
this change.** The modules are implemented and unit-tested in isolation; the
wiring below is the handoff.

Status:

- **Implemented & tested (module level):** `tradingagents/contracts/rating.py`,
  `tradingagents/rating_authority.py`, `tradingagents/security/*`,
  `scripts/security_regression.py`, fixtures.
- **Not yet wired into the real graph:** the commit gate, sanitisation of fetched
  fields, prompt-payload redaction, and role tool-guard are *called* only in
  tests today. See "Wiring" for exact call sites.

## Rating authority (REQ-INV-003)

Single commit entry point:

```python
from tradingagents.rating_authority import commit_rating
from tradingagents.contracts.rating import Provenance, InMemoryRatingStore

result = commit_rating(
    candidate=final_state["final_trade_decision"],   # model text OR structured tier
    provenance=provenance,                            # verified run provenance
    store=store,                                      # read(id)/write(id, record)
    decision_id="AAPL:2026-11-18:<run-signature>",    # stable, unique per decision
)
# Provenance must set snapshot_verified=True explicitly (it defaults to False);
# Part 1 is responsible for actually verifying the snapshot, not Part 5.
# result.rating        in {Buy,Overweight,Hold,Underweight,Sell,REVIEW}
# result.review_required  True iff rating == REVIEW
# result.reason_codes  ("ok",) | ("missing_provenance",) | ...
```

Failure semantics:

- Provenance missing/invalid/unverified -> `REVIEW`, nothing written.
- Candidate with no readable call -> `REVIEW`, nothing written.
- Out-of-set candidate -> `REVIEW`, nothing written.
- Re-commit validates the **request** provenance first: an unverified/invalid
  request is refused (REVIEW) even if it matches a stored record.
- Same `decision_id` + same rating + same (valid) source -> returns the
  **originally persisted provenance** (idempotent retry; not a new claim).
- Different rating OR different source for an existing id -> `CONFLICT`
  (`review_required`), nothing written.
- Corrupt stored record **fails closed**: `REVIEW` / `review_required=True` /
  `is_tradeable=False`; `PERSISTED_OUT_OF_SET` (rating out of set) or
  `CORRUPT_RECORD` (missing/malformed source, unverified flag, or `decision_id`
  mismatch), nothing overwritten.
- Records persist `snapshot_verified`; read/retry trusts the source only if all
  fields are present, structurally valid, and `snapshot_verified is True` (Part 1
  sets that flag after real verification).
- Blank `decision_id` -> refused, nothing written (no shared default key).
- **Serial idempotency only:** atomic concurrent commit is the store's (Part 3)
  responsibility; the store contract is `read(id)`/`write(id, record)`.

### Part 1 — required integration points

| # | Location | Required call | Verification scenario |
|---|---|---|---|
| 1a | `graph/trading_graph.py::record_decision`, before `store_decision` | build `Provenance(snapshot_id, manifest_id, model, prompt_version, config_version, snapshot_verified=...)` from the run's **real** verified snapshot/manifest/versions; set `snapshot_verified=True` only after checking the market data | when the snapshot is unverified or a version is missing, the run's rating is `REVIEW` (never a tier) |
| 1b | same | `commit_rating(candidate=final_state["final_trade_decision"], provenance, store, decision_id=<ticker:date:run-signature>)` | valid provenance + labelled call commits a tradeable tier; retry with same request returns the stored source |
| 1c | same | persist memory-log rating from `result.rating`; surface `result.review_required`/`reason_codes` | `REVIEW` decisions are recorded as needing review, not as a fabricated Hold |
| 1d | analyst prompt assembly | `sanitize(fetched_text)` for every news/social/user field | an injected fetched field cannot change the committed rating (offline adapter test covers the logic) |
| 1e | model-call boundary | `safe_prompt_payload(messages)` | no secret in the payload before the call |
| 1f | tool dispatch | `ToolGuard(allowed=...).call(role, tool, executables, ...)`; catch `UnauthorizedToolCall` and continue | unbound tool executes 0 times; `TOOL_REJECTED` logged |
| 1g | logging setup (once, after config) | `install_log_filter()`; `register_handler(h)` for later handlers; handle `propagate=False` loggers | a registered non-pattern key from a child logger never reaches output |
| 1h | run teardown / manifest hooks | `drain_events()` for security events | every detection/validation/rejection appears in the manifest |

`run_rating(final_state)` in `agents/rating.py` remains the backward-compatible
reader; the authority's `resolve_rating` shares the same parser, so there is no
second implementation.

### Part 3 — required integration points

| # | Location | Required call | Verification scenario |
|---|---|---|---|
| 3a | records store | implement `read(decision_id)` / `write(decision_id, record)` per `contracts/rating.Store`; **atomic per id** (serial idempotency is all Part 5 promises) | concurrent writers do not produce two committed ratings for one id (Part 3 test) |
| 3b | same | persist the record **including `snapshot_verified`**; do not mutate the rating | read-back of a valid record returns the tier; tampered/partial records read as `REVIEW` |
| 3c | manifest writer | `scrub_manifest(manifest)` before writing `manifest.json`/reports | a synthetic key in any field is absent from the written artifact |
| 3d | manifest writer | include `drain_events()` as `security_events` and `result.rating`/`reason_codes`/provenance as the final rating | manifest replays to the same rating; schema valid |

Part 5's write gate already refuses an out-of-set value before `write` and
`read_committed_rating` re-validates (fail-closed), so a faulty writer cannot
persist a bad tier unbeknownst to us. The record shape written by Part 5 is:

```python
{"rating", "decision_id", "snapshot_id", "manifest_id",
 "model", "prompt_version", "config_version", "snapshot_verified"}
```

Part 3 must preserve `snapshot_verified` verbatim; on read/retry Part 5 trusts
provenance only when all fields are present, structurally valid, and
`snapshot_verified is True`.

## Untrusted input/output (REQ-SEC-001)

### Sanitise fetched fields before they enter a prompt (Part 1 analysts)

```python
from tradingagents.security import sanitize
safe_block = sanitize(news_or_post_or_user_text)   # delimited, injection dropped
```
Call this on every news/social/user text assembled into an analyst prompt. A
dropped field returns `""`; use `sanitize_detailed` when you also need
`dropped`/`events`.

### Validate model output before it becomes state (Part 1)

```python
from tradingagents.security import validate_output
res = validate_output(parsed, SCHEMA, references=known_evidence_ids)
if not res.ok:
    drop_it(res.errors); continue           # res.value is None; event logged
```
Only `res.value` (when `ok`) may be written to state.

### Role tool-guard before execute (Part 1 graph dispatch)

```python
from tradingagents.security import ToolGuard, UnauthorizedToolCall
guard = ToolGuard(allowed={"market_analyst": {"get_stock_data"},
                           "news_analyst": {"get_news"}})
try:
    result = guard.call(role, tool_name, executables, *args, **kwargs)
except UnauthorizedToolCall as exc:      # caught here, run continues
    log.warning("tool rejected: %s", exc)
```
`ToolGuard.call` raises **before** looking up the executable, so a rejected tool
never executes. Catch `UnauthorizedToolCall` at the dispatch layer and continue.

### Security events (Part 1/3)

`tradingagents.security.get_event_log()` collects redacted `SecurityEvent`s.
Part 3 should call `drain_events()` and put them in the manifest's
`security_events` list; Part 1 can drain per-run.

## No secret leakage (REQ-INV-004)

### Central redaction

```python
from tradingagents.security import redact, safe_prompt_payload, scrub_manifest
```
- **Logs (handler-level):** `install_log_filter()` installs a redacting filter on
  the **existing handlers** of the root logger and its subtree (so child-logger
  records that propagate are covered); `register_handler(handler)` installs on a
  single handler. Filters are **not** attached to loggers (those miss propagated
  child records) and nothing global is monkeypatched.
  - **Composition-root responsibility (Part 1):** call `install_log_filter()`
    once after logging is configured, and `register_handler()` on any handler
    added later; for a third-party logger with `propagate=False`, register its
    handlers too or set `propagate=True`. Part 5 provides the interface; Part 1
    installs it. Redaction covers `record.msg`, deferred `%` args, and the full
    traceback text (type kept, secret removed).
- **Prompts / model payload:** wrap the assembled payload with
  `safe_prompt_payload(messages)` right before the model call (Part 1/2).
- **Manifest / report:** wrap with `scrub_manifest(obj)` right before Part 3
  writes to disk.
- **Exceptions:** `redact(exception)` returns the same exception type with a
  scrubbed message.

Redaction draws on (a) the actual key values the process read from the
canonical provider env vars and (b) well-known token patterns. It reads keys
from the **environment only**, matching the existing client chain
(`llm_clients/openai_client.py` uses `os.environ.get(get_api_key_env(...))`); no
`resolve_api_key` duplicate was added.

## Demonstration (offline, reproducible)

- Invalid rating -> REVIEW: see `tests/req/test_rating_invariant.py::test_fuzz`
  and `::test_requires_provenance`.
- Unauthorised tool rejected (0 executions):
  `tests/security/test_prompt_injection.py::test_no_unauthorized_tool_calls`.
- Synthetic secret redacted in logs/exception/manifest/payload:
  `tests/security/test_secret_redaction.py::test_artifacts` / `::test_redaction`.
- Metrics harness: `python scripts/security_regression.py --all`.
