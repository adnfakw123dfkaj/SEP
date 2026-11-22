# Invariant Register

Every invariant with its statement, source requirement, enforcing component,
verification method, and an operational fallback if violated (a concrete action,
not "fix the bug").

| ID | Statement | Source | Enforcing component | Verification | Fallback on violation |
|---|---|---|---|---|---|
| REQ-INV-001 | A decision record is written as one atomic unit; re-running the same `(ticker, trade_date, run_signature)` never appends a second entry. | REQ-INV-001 | `records/atomic.py`, `records/idempotency.py`, `memory/log.py` | `pytest tests/req/test_records.py` | Quarantine the partial staging dir (delete it), keep the previous complete record; log the event and skip the duplicate write. |
| REQ-INV-002 | No data item dated after the analysis date may enter any agent input. | REQ-INV-002 | `dataflows/date_window.py`, vendor `withhold_*`, `memory.get_past_context(as_of=)` | `pytest tests/req/test_point_in_time.py` | Drop the offending item; if a live-only source cannot be dated, replace with an `<unavailable>` marker and lower confidence. |
| REQ-INV-003 | The committed rating is exactly one of `{Buy, Overweight, Hold, Underweight, Sell, REVIEW}`, produced by deterministic code; missing provenance → `REVIEW`. | REQ-INV-003 | `agents/rating.py`, `rating_authority.py`, `graph/trading_graph` commit gate | `pytest tests/req/test_rating_invariant.py` | Do not persist a trade rating; record `REVIEW` with reason codes and route to human/rerun. |
| REQ-INV-004 | Secrets never appear in logs, reports, manifest, prompts or errors. | REQ-INV-004 | `security/redaction.py`, `dataflows/net.get_scrubbed`, `llm_clients/api_key_env.py` | `pytest tests/security/test_secret_redaction.py` | Redact to `***`, drop the payload that carried the secret, and raise an operator-visible security event. |

Notes:
- Each invariant is zero-tolerance (no slack threshold); a single escape is a
  failure.
- The gate-level invariants (test approval, regression, AI-use log) are governed
  by `docs/gate-intro.md` and enforced by `scripts/gates/`.
