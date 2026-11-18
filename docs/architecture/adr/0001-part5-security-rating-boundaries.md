# ADR-0001 — Part 5 security & rating authority boundaries

- Status: Accepted (module-level; integration pending)
- Date: 2026-11-18
- Owner: 陈妍妍
- Scope: Part 5 (`contracts/rating.py`, `rating_authority.py`, `security/`)
- Note on location: the repository had no `docs/architecture/adr/` directory and
  no other ADR convention. This ADR creates the standard
  `docs/architecture/adr/NNNN-title.md` layout; later ADRs should follow it.

## Context

The final committed rating must be deterministic and the pipeline reads
untrusted text (news, social posts, user input) and holds credentials. LLM output
is advisory. Several trust boundaries need an explicit decision so Part 1
(composition root) and Part 3 (records/manifest) integrate against a clear
contract without Part 5 reaching into their code.

## Decisions

### 1. Rating authority (REQ-INV-003)

- **Single entry point:** `rating_authority.commit_rating(candidate, provenance,
  store, decision_id=...)`. The committed value is exactly one of
  `{Buy, Overweight, Hold, Underweight, Sell, REVIEW}`.
- **Model output is advisory:** `candidate` is parsed/validated deterministically
  (reusing `agents/rating.py`); free text cannot override a structured call. No
  labelled call -> `REVIEW`.
- **Commit prerequisites:** verified `Provenance` (structurally well-formed
  `snap-<hex>` / `man-<hex>` ids, model id, version pins) **and**
  `snapshot_verified is True`. Any failure -> `REVIEW` with a reason code; nothing
  is written.
- **Source trust — who verifies what:**
  - Part 5 verifies *structure* (id shapes, version formats) and that the caller
    asserted `snapshot_verified`. `snapshot_verified` **defaults to `False`**: it
    is never implied by constructing a `Provenance`.
  - Part 1 (composition root) is responsible for *actually* verifying the
    snapshot against the real market data source and setting
    `snapshot_verified=True` only then. Part 5 cannot re-verify the underlying
    market data.
- **Re-commit policy (serial idempotency):** the **request provenance is
  validated first**; an unverified/invalid request is refused even if its
  fingerprint matches a stored record. Then:
  - same rating **and** same source fingerprint -> return the **originally
    persisted provenance**, `reason_codes == ("ok",)`.
  - different rating, or different source -> `CONFLICT` (`review_required`),
    nothing written.
  - **any corrupt stored record fails closed**: `rating == REVIEW`,
    `review_required is True`, `is_tradeable is False`, with an accurate reason.
    `PERSISTED_OUT_OF_SET` for an out-of-set rating; `CORRUPT_RECORD` for other
    damage (missing/malformed source, unverified flag, or `decision_id` not
    matching the queried id). Nothing is overwritten. A corrupt **Buy** record is
    never surfaced as a tradeable Buy.
  - blank `decision_id` -> refused (no shared default key).
- **Persistence content & verification boundary:** each record stores rating +
  the full source fields (`snapshot_id, manifest_id, model, prompt_version,
  config_version`) **and the persisted `snapshot_verified` flag**. On read/retry
  the source is reconstructed **only if** all fields are present, they pass the
  same structural validation as a live commit, **and** the record's
  `snapshot_verified is True`. A record's existence alone never proves its
  source was verified. Who verifies: Part 1 (the trusted source layer) sets
  `snapshot_verified=True` on commit after checking the real market data; Part 5
  persists that flag, re-validates structure, and refuses anything it cannot
  trust — it does not itself re-verify the market data.
- **Concurrency:** only *serial* idempotency is promised here. Atomicity under
  concurrent writers is the store's responsibility (Part 3); see the store
  contract in `contracts/rating.py` and `docs/part5-integration.md`.

### 2. Untrusted input/output (REQ-SEC-001)

- **Sanitise before prompt:** `sanitize(text) -> str` (simple) and
  `sanitize_detailed(text) -> SanitizedText` (detail). Control chars stripped,
  injection-shaped text **dropped** (not merely warned), forged delimiters
  neutralised, length bounded, facts preserved. Detection targets instruction
  structure, not ordinary financial words.
- **Validate before state:** `validate_output(value, schema, references=...)`
  checks the documented schema subset (type/enum/required/items/ref). **Reference
  checks fail closed:** a schema using `ref=True` with `references=None` is a
  configuration error (rejected), never a silent pass. An empty set means no id
  is valid.
- **Tool guard:** `ToolGuard.call` rejects a role's unbound tool **before** it
  executes (the executable is never looked up on the reject path); raises
  `UnauthorizedToolCall`; logs a redacted `TOOL_REJECTED`; the caller (graph
  dispatch, Part 1) catches it and continues.
- **Events:** every detection/validation/rejection is a `SecurityEvent`,
  redacted before storage; drainable into a manifest by Part 3.

### 3. Secret non-leakage (REQ-INV-004)

- **Unified entry points:** `redact(value)`, `redact_text`, `redact_obj`,
  `safe_prompt_payload`, `scrub_manifest`.
- **Logging is handler-level:** `register_handler(handler)` attaches a
  `RedactingFilter` to one handler; `install_log_filter(logger)` installs on the
  existing handlers of `logger` and its subtree. Handler-level is chosen because
  a logger filter does not see records that *propagate up* from child loggers.
  - No global monkeypatching of `logging.Handler`/`addHandler`.
  - New handlers added later are the **composition root's** responsibility
    (call `register_handler`); a third-party logger with `propagate=False` must
    also be handled by the composition root. Part 5 provides the reliable
    interface; Part 1 installs it.
- **Sources of truth:** the actual env-key values for known providers (read from
  the environment only) plus well-known token patterns. No file-sourced key.
  Normal SDK authentication is untouched (no `resolve_api_key` added; the client
  chain still reads `os.environ.get(get_api_key_env(...))`).
- **Exceptions:** the full traceback text is rebuilt, redacted, and stored in
  `exc_text` (with `exc_info` cleared) so type/traceback shape is preserved but
  the secret is removed.

## Failure policy (summary)

| Condition | Result | Written? |
|---|---|---|
| valid rating + valid committed provenance | tradeable tier | yes |
| missing/invalid/unverified provenance | `REVIEW` (+reason) | no |
| unparseable candidate / out-of-set | `REVIEW` (+reason) | no |
| existing same rating+source retry | original value + original source, ok | no |
| existing different rating/source | `CONFLICT` | no |
| corrupt record (out-of-set / missing fields) | `PERSISTED_OUT_OF_SET` / `CORRUPT_RECORD` | no |
| injection-shaped text | dropped + event | n/a |
| ref schema without references | config error (reject) | no |
| unbound tool | `UnauthorizedToolCall` (0 executions) | n/a |

## Alternatives considered

- **Logger-level filter only** (rejected): does not see propagated child records.
- **Global `addHandler` monkeypatch** (rejected): surprises third parties and is
  hard to reason about; explicit handler-level install is chosen instead.
- **"Any non-empty string is a verified source"** (rejected): structure + explicit
  verification flag only.
- **Silent overwrite on re-commit** (rejected): hides conflicting sources; a
  conflict is surfaced instead.
- **Full JSON Schema validator** (not implemented): the requirement names
  structure/type/enum/reference; a documented small subset is used rather than a
  partial re-implementation claiming full support.

## Consequences

- Part 1 must set `snapshot_verified` truthfully and install the log filter on
  its handlers; Part 3 must implement the `Store` contract and use
  `scrub_manifest`/`drain_events`. Documented in `docs/part5-integration.md`.
- REVIEW becomes a normal, auditable outcome; callers must handle it.
