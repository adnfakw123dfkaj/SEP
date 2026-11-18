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
# result.rating        in {Buy,Overweight,Hold,Underweight,Sell,REVIEW}
# result.review_required  True iff rating == REVIEW
# result.reason_codes  ("ok",) | ("missing_provenance",) | ...
```

Failure semantics:

- Provenance missing/invalid/unverified -> `REVIEW`, nothing written.
- Candidate with no readable call -> `REVIEW`, nothing written.
- Out-of-set candidate -> `REVIEW`, nothing written.
- Same `decision_id` re-committed -> returns the existing value (idempotent).
- Blank `decision_id` -> `REVIEW`, nothing written (no shared default key).

### Where Part 1 wires it in

In `tradingagents/graph/trading_graph.py::record_decision`, before
`self.memory_log.store_decision(...)`, Part 1 should:

1. Build a `Provenance` from the run's verified snapshot id, evidence manifest
   id, and the model/prompt/config versions actually used.
2. Call `commit_rating(...)` with `decision_id` derived from ticker + trade date +
   run signature.
3. Persist the memory-log rating from `result.rating` (never from the raw text),
   and surface `result.review_required`/`reason_codes` to the caller.

`run_rating(final_state)` in `agents/rating.py` remains the backward-compatible
reader; the authority's `resolve_rating` shares the same parser, so there is no
second implementation.

### Where Part 3 wires persistence

Part 3's records store should implement the two-method `Store` protocol from
`tradingagents/contracts/rating.py` (`read(decision_id)` / `write(decision_id,
record)`). Part 5's write gate already refuses an out-of-set value before
`write` and re-validates on `read_committed_rating`, so a faulty writer cannot
persist a bad tier unbeknownst to us. The record shape written is:

```python
{"rating", "decision_id", "snapshot_id", "manifest_id",
 "model", "prompt_version", "config_version"}
```

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
- **Logs:** `install_log_filter()` on the root logger (or your logger) — redacts
  `record.msg`, deferred `%` args, and exception text.
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
