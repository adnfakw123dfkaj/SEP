# SEP — TradingAgents (CS5351 Agentic Software Engineering Project)

A multi-agent LLM trading-research tool: given a ticker and an analysis date, a
LangGraph pipeline of specialist agents (market/sentiment/news/fundamental
analysts → bull/bear research debate → research manager → trader → risk debate →
portfolio manager) produces a 5-tier rating (Buy/Overweight/Hold/Underweight/Sell
or REVIEW) plus the reports behind it, with deterministic rating authority,
point-in-time data, an evidence chain and a per-run manifest. Advisory only — no
order execution.

- Repository: https://github.com/adnfakw123dfkaj/SEP
- Application lives in `tradingagents/` (package `tradingagents` + `cli`).
- Requirements: `docs/req/requirements.yaml` (D1). Architecture: `architecture-blueprint.md` + `docs/architecture/` (D2). Governance: `docs/code-governance/`, `AGENTS.md`, `.opencode/`, `.agent/` (D3/D4).

## How it works (brief)

CLI → `TradingAgentsGraph` → LangGraph workflow. Analysts run in parallel; the
research and risk debates are bounded sequential turns; the composition root
(`graph/trading_graph.py`) is the single writer of the run record and the rating.
Data flows through `dataflows/router.py`; models through `llm_clients/`; safety,
cost and rating authority are enforced by guards. See `architecture-blueprint.md`.

## Project file organization

- `AGENTS.md`, `architecture-blueprint.md`, `Prompt.md`, `.opencode/`, `.agent/` — coding-agent governance (D3, D9).
- `docs/req/` — machine-readable requirements + schema (D1).
- `docs/architecture/` — 11 D2 artifacts (ADR, invariants, trace matrix, memory, permission, runtime policy, evaluation table, …).
- `docs/code-governance/` — structural/verification constraints, tool manifest; `docs/{review-memo,debt-register,bug-diary}.md` (D3/D4).
- `prompts/` — versioned runtime prompts (D9).
- `src/` — D8 compatibility entry; points to the application source in `tradingagents/`.
- `tradingagents/` — application source (`tradingagents` package + `cli`) and tests.
- `test/offline/`, `test/live/` — D8 root entry points; delegate to `tradingagents/test/offline` and `tradingagents/test/live`.
- `.github/workflows/` — CI and blocking gates G1–G7.

## Running tests

From the repository root, the D8 entry points are:

```bash
./test/offline/run.sh
./test/live/run.sh
```

The underlying commands run from `tradingagents/`:

**Offline (deterministic, no network, no live API)** — the CI suite:

```bash
cd tradingagents
python -m pytest tests -q -m "not integration"      # or ./test/offline/run.sh
```

**Live (requires provider API keys / quota; network)**:

```bash
cd tradingagents
python -m pytest tests -q -m integration            # or ./test/live/run.sh
```

**Full suite** (offline + live): drop the `-m` filter:

```bash
cd tradingagents
python -m pytest tests -q
```

Configuration is read from `tradingagents/.env` (e.g.
`TRADINGAGENTS_LLM_PROVIDER=deepseek`, `DEEPSEEK_API_KEY=...`,
optional `FRED_API_KEY=...`). Run from the `tradingagents/` directory so the
`.env` is found.

## Blocking CI

The CI blocks merges via gates G1–G7 (test approval, static analysis, schema,
semantic evaluation, regression, AI-use log, ownership). The gate rules live only
on `master`; see `docs/gate-intro.md` and `docs/code-governance/gates-deployment.md`.
