# Architecture Blueprint

> D2.1 — the master constraint document the Plan agent reads. It fixes scope,
> architectural drivers, boundaries, components, authority boundaries, the agent
> workflow, permissions, verification, observability and change policy. Every
> other `docs/architecture/*` artifact elaborates one section of this file.

## 1. Scope

TradingAgents is a research tool: given a ticker and an analysis date, a
multi-agent LangGraph pipeline produces a 5-tier rating
(`Buy/Overweight/Hold/Underweight/Sell`) or `REVIEW`, plus the reports behind it.
It is **advisory only** — no order execution, no cash ledger. The repository
under `tradingagents/` is the application; `cli/` is its command surface.

Out of scope (per `requirements-final.md` §0.3): automatic trading, model
fine-tuning/RL, full market coverage, a web front-end, production alerting.

## 2. Architectural drivers

- **D1 Point-in-time integrity** (REQ-INV-002) — no data dated after the run date
  may reach any agent.
- **D2 Deterministic authority** (REQ-INV-003) — the AI proposes; deterministic
  code commits the rating, or `REVIEW`.
- **D3 Safety of untrusted input/output** (REQ-SEC-001, REQ-INV-004) — fetched
  text and model output are sanitised/validated; secrets never leak.
- **D4 Auditable records** (REQ-FR-004, REQ-INV-001) — every run yields a
  manifest and an evidence chain; the decision record is atomic and idempotent.
- **D5 Latency & token cost** (REQ-PER-001, REQ-COST-001) — tiered profiles,
  per-profile token budget, hard stop over budget.
- **D6 Structured, evaluable debate** (REQ-FR-003, REQ-QUAL-001) — debate turns
  are typed and measured.
- **D7 Configurable profiles & preflight** (REQ-FR-001, REQ-FR-002).

## 3. System boundaries

```
CLI (cli/) ──► TradingAgentsGraph (graph/) ──► LangGraph workflow (graph/setup.py)
                    │                                   │
                    ├─ LLM tiers (llm_clients/)         ├─ Analysts ∥ Memory Log
                    ├─ Guards: cost (cost/), security   ├─ Bull⇄Bear → Research Mgr
                    │   (security/), rating authority   ├─ Trader
                    ├─ Memory (memory/)                 └─ Risk 3-way → Portfolio Mgr
                    └─ Data layer (dataflows/) ──► vendors
```

Trust boundaries: (1) external vendors → `dataflows/router`; (2) provider LLM
responses → `cost`/`security` guards → agents; (3) agent output → deterministic
authority (`graph/trading_graph`, `rating_authority`) → persisted record.

## 4. Components (map to packages)

- `graph/` — orchestration: `TradingAgentsGraph`, `GraphSetup`, `ConditionalLogic`,
  `Propagator`, `checkpointer`, `analyst_execution`.
- `agents/` — analysts (market, sentiment, news, fundamentals), researchers
  (bull/bear), managers (research, portfolio), trader, risk debators; contracts,
  schemas, `tools.py`, `rating.py`, `post_screen.py`.
- `dataflows/` — vendor routing (`router.py`), point-in-time (`date_window.py`),
  symbols, caches, errors, files/locks, vendors (yahoo, alpha_vantage, sec_edgar,
  fred, polymarket, reddit, stocktwits).
- `llm_clients/` — provider registry and per-provider quirks.
- `memory/` — decision log, settlement, reflection.
- `contracts/` — typed records (profile, debate, manifest, evidence, cache,
  rating, llm_event, cost).
- `coding cost/` — estimator, budget, router, monitor, guard, enforcement, audit.
- `evidence/` — registry, fidelity, claims.
- `records/` — atomic write, idempotency.
- `security/` — sanitize, validate, redaction, tool-node guard.
- `cache/`, `resilience.py`, `preflight.py`, `profiles.py`, `rating_authority.py`,
  `reporting.py`, `report_html.py`, `portfolio.py`, `backtest.py`.

## 5. Authority boundaries (advisory vs authoritative)

| Layer | Authority | Notes |
|---|---|---|
| LLM agents (analysts, researchers, traders, risk) | **Advisory** | Produce reports/turns/plans as text. |
| `agents/rating.py` + `rating_authority.py` | **Authoritative** | Deterministically maps to the closed set or `REVIEW`. |
| `graph/trading_graph` commit gate | **Authoritative** | Only write path for the final rating; blocks on missing provenance. |
| `memory/log` + `records/` | **Authoritative** | Persisted record; atomic + idempotent. |
| `security/`, `cost/guard` | **Enforcement** | Block/deny actions; do not decide the trade. |

## 6. Agent workflow

`START → {analysts (parallel) + Memory Log} → Bull⇄Bear (bounded debate) →
Research Manager → Trader → Aggressive⇄Conservative⇄Neutral (bounded risk debate)
→ Portfolio Manager → END`. Analysts run concurrently (asyncio in one process);
debates and the manager chain are sequential (data-dependent). Per-analyst
subgraph holds its own message history and tool rounds. Routers use complete path
maps; recursion limit guards tool rounds.

## 7. Permissions

The gate permission model (D3 `.opencode/permissions.jsonc`) governs the coding
agent, not the trading agents. Inside the app: agents may call only their bound
tools (security tool-node guard); no agent writes files or commits ratings except
through the composition root. See `permission-model.md`.

## 8. Verification strategy

Three tiers (see `docs/code-governance/verification-constraints.md`): structural
(imports/module boundaries/permission), regression (`pytest` full suite), and
behavioural (quality/faithfulness/safety thresholds, zero safety escapes). Every
requirement's fit criterion is a metric+threshold+verification in
`docs/req/requirements.yaml` and is mapped in `trace-matrix.md`.

## 9. Observability

Per-run `RunManifest` (token/cost, fallback/security events, vendor versions,
rating, status); memory log for cross-run outcomes; gate self-tests and CI status
checks. See `runtime-policy-catalog.md` for failure handling.

## 10. Change policy

- Contracts (`contracts/*`) change only via PR + owner approval + updated
  contract tests.
- Safety-relevant paths (`tradingagents/{agents,memory,dataflows,security,contracts,graph}/`,
  `scripts/gates/`) require human review and, per the course D7, an accompanying
  architecture decision record.
- The gate rule set lives only on `master`; changes to it follow
  `docs/gate-intro.md`.
