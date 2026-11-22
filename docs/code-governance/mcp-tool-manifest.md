# MCP / Tool Manifest

The tools the coding agent (and the trading agents) may call, and which roles may
call them. This repository has **no MCP server**; below are the concrete tool
surfaces that exist and their allowlists.

## 1. Trading-agent tools (in-app, `tradingagents/agents/tools.py`)

Each analyst receives only its bound tools; `security/tool_guard.py` rejects a
proposal outside the role's allowlist before execution (REQ-SEC-001).

| Role | Allowed tools |
|---|---|
| Market Analyst | `get_stock_data`, `get_indicators`, `get_verified_market_snapshot` |
| News Analyst | `get_news`, `get_global_news`, `get_macro_indicators`, `get_prediction_markets` |
| Fundamentals Analyst | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement`, `get_insider_transactions` |
| Sentiment Analyst | _none_ (sources pre-fetched into the prompt) |
| Bull / Bear / Managers / Trader / Risk / Portfolio Manager | _no tools_ (reason over provided context) |

Every dated tool reads the run's `trade_date` from graph state and clamps the
served window (REQ-INV-002).

## 2. Coding-agent tools (repository maintenance)

The coding agent operates through its host (OpenCode) command surface, bounded by
`.opencode/permissions.jsonc`. The relevant project tools it may invoke:

| Tool | Purpose | Allowed for |
|---|---|---|
| `python -m pytest ...` | run tests | coding agent, verification agent, humans |
| `ruff check`, `pyright` | lint / type check | coding agent, verification agent |
| `python scripts/gates/run.py <g1..g7> --input ...` | run one gate decision | verification agent, CI |
| `python scripts/gates/run_static_checks.py` | contract/security/api/permission checks | verification agent, CI |
| `python scripts/gates/collect_context.py ...` | collect gate inputs | CI, verification agent |
| `python tradingagents/scripts/{token_audit,bench_latency,bench_preflight}.py` | cost/latency audits | humans (owner-run) |
| `python scripts/security_regression.py` | injection/secret regression | verification agent, CI |

**Forbidden for the coding agent**: writing under safety-relevant paths without an
approval + ADR + human review; editing `docs/approvals/**`, `docs/req/**` schema,
or gate rule definitions without a gate-owner review (see `.opencode/permissions.jsonc`).

## 3. Role → capability summary

- **Coding agent**: may read the repo and edit whitelisted paths; may run tests/
  lint/type locally; **may not** self-approve safety-critical changes.
- **Verification agent**: may run all checks and gates read-only; **may not** edit
  code or approvals.
- **Human owner**: approves safety-critical changes, runs live/integration tests,
  and is the only authority for merges to `master` and for gate-config changes.
