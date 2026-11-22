# Permission Model

File-level read/write rights for each AI agent role in the trading pipeline, and
the tool-call allowlist. Default is **no read, no write**; every path and tool is
explicitly granted.

## 1. Trading agents — filesystem

Trading agents are pure in-memory reasoning nodes. They do **not** read or write
arbitrary files. Writes happen only through the composition root.

| Agent role | Reads | Writes |
|---|---|---|
| Market Analyst | tool results (in-memory) | — |
| Sentiment Analyst | pre-fetched vendor blocks | — |
| News Analyst | tool results | — |
| Fundamentals Analyst | tool results | — |
| Bull / Bear Researcher | state reports | — |
| Research Manager | debate history | — |
| Trader | plan + market report + portfolio | — |
| Aggressive/Conservative/Neutral | reports + trader plan | — |
| Portfolio Manager | risk history + lessons | — |
| Composition root (`trading_graph`) | all state | run-state JSON, report tree, manifest, memory log, checkpoints, rating records (atomic) |

## 2. Trading agents — tool allowlist (REQ-SEC-001)

Each agent may call only the tools bound to its role; `security/tool_guard.py`
rejects (before execution) any tool outside the allowlist and logs a
`tool_rejected` event. Current binding:

| Analyst | Tools |
|---|---|
| Market | `get_stock_data`, `get_indicators`, `get_verified_market_snapshot` |
| News | `get_news`, `get_global_news`, `get_macro_indicators`, `get_prediction_markets` |
| Fundamentals | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement`, `get_insider_transactions` |
| Sentiment | none (sources pre-fetched) |

Roles bound to no tools cannot call any; any proposal is rejected.

## 3. Coding agent (D3 — `.opencode/permissions.jsonc`)

The AI coding agent that edits this repository is separately governed by
`.opencode/permissions.jsonc` and `.opencode/rules.md`: default no read/write,
every path explicitly whitelisted, safety-relevant paths require review. See those
files.
