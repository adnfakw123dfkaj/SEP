# Runtime Policy Catalog

What the system does when each degraded or failure path is triggered. Each path
maps to a concrete behavior and an evidence event; none silently continues with
fabricated data.

| Trigger | System behavior | Evidence |
|---|---|---|
| Vendor throttled / unreachable while other vendors configured | Try next vendor in the configured chain. If all unavailable, return `DATA_UNAVAILABLE` sentinel (not the instrument's fault). | router log; manifest `fallback_events` |
| Vendor answered "no data" for the symbol | Return `NO_DATA_AVAILABLE` sentinel; never fabricate. | router log `no_data_available` |
| Optional enrichment vendor fails (`macro_data`, `prediction_markets`) | Degrade to a sentinel; proceed without it. | manifest `fallback_events` |
| Yahoo returns a stale OHLCV frame (>10 days) | Reject as `NoMarketDataError(stale)`; try next vendor. | router log |
| Live-only source on a historical run (profile, insider, statements, social) | Withhold with an `<unavailable>` notice (REQ-INV-002). | report text / manifest as-of |
| LLM provider error | Bounded retry, then fallback to the cheaper tier (`FallbackLLM`); if still failing, the rating authority records `REVIEW`. | `fallback_events`; rating reason codes |
| Rating missing provenance (snapshot not verified / manifest / version pin absent) | Commit gate refuses; status `REVIEW`. | rating record reason codes |
| Model proposes a tool not bound to its role | Reject before execution; log `tool_rejected`; continue. | manifest `security_events` |
| Fetched text / model output suspicious or out-of-schema | Sanitised / validated before use; dropped or recorded; cannot change the rating. | `security_events` |
| Secret detected in an output sink | Redact to `***`; drop the payload; raise security event. | redaction log |
| Token hard budget would be exceeded before a call | `GuardedLLM` raises `BudgetExceededError`; run ends `budget_exceeded` / `REVIEW` (does not degrade/rout). | `CostReport`, status |
| Run interrupted (opt-in `--checkpoint`) | Resume from last successful node via SqliteSaver; cleared on clean completion. | checkpoint metadata |
| Memory log unreadable / settlement fails | Run continues; report notes it; entries stay pending for retry. | `memory_note` |

## Observability surfaces

- `RunManifest`: token/cost, vendor versions, cache hits, fallback/security events,
  rating, status, timestamps.
- CI gates (`docs/gate-intro.md`): G1–G7 block merges on violations.
- Gate self-tests (`tests/gates`) and full `pytest` regression.
