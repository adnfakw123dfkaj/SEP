# Memory / State Design

What state survives across sessions, interruptions and versions; write and
retrieval policy; ownership; retention; privacy.

## 1. What persists, and where

| State | Location (default) | Survives | Owner |
|---|---|---|---|
| Decision memory log | `~/.tradingagents/memory/trading_memory.md` | process restart, sessions, versions | `memory/log.py` |
| Run state JSON | `<results_dir>/<ticker>/TradingAgentsStrategy_logs/full_states_log_<date>.json` | on disk | `graph/trading_graph._log_state` |
| Report tree + HTML | `<results_dir>/reports/<ticker>_<stamp>/` | on disk | `reporting.py` |
| Data caches | `~/.tradingagents/cache/` (CSV, SEC 24h) | TTL-dependent | `dataflows/*` |
| Checkpoints | `~/.tradingagents/cache/checkpoints/<TICKER>.db` (opt-in) | until cleared | `graph/checkpointer.py` |
| Decision records (atomic) | alongside memory (`rating_records/`, `records/`) | on disk | `records/` |

## 2. Write policy

- **Memory log**: append-only; one entry per `(ticker, trade_date)` (idempotent
  guard); written under a cross-process lock; settled entries updated via temp
  file + `os.replace`.
- **Run state / reports / manifest**: produced at the end of a run by the
  composition root; the decision record is written atomically as one unit
  (REQ-INV-001) — either the previous complete record or the new one.
- **Checkpoints**: written per node when `--checkpoint` is enabled; cleared on
  clean completion.

## 3. Retrieval policy

- `get_past_context(ticker, n_same=5, n_cross=3, as_of=...)`: recent same-ticker
  decisions and cross-ticker lessons, injected into the Portfolio Manager. A
  historical run passes `as_of` so only lessons resolved by that date are used
  (REQ-INV-002).
- Pending (unsettled) entries are not retrieved as lessons until their holding
  window has traded and a reflection exists.

## 4. Retention

- `memory_log_max_entries` (default `None`) caps resolved entries; when set, oldest
  resolved entries are pruned; pending entries are never pruned.
- Caches expire by TTL (OHLCV same-day 900s / historical day; SEC 24h).
- Checkpoints cleared on success.

## 5. Privacy

- The memory log stores decisions and reflections (no raw vendor payloads beyond
  what the decision text already contains).
- Secrets are never written (REQ-INV-004; `security/redaction.py`).
- Reports and manifests are local files under the user's data directory; nothing
  leaves the machine except provider requests.
