# Evaluation Logbook

Accumulated evidence behind the architecture choices (optional D2 artifact).

## 2026-11 baseline (from `requirements-final.md` §0.1)
- NVDA/2026-11-10, market analyst only: ~425 s, rating Sell.
- NVDA/2026-11-14, market+social: ~550 s, rating Underweight.
- Findings: Reddit HTTP 403 (sentiment low confidence); StockTwits + Yahoo news
  usable; token/cost not summed; free-text debate hard to evaluate; full 4-analyst
  default slow.

## Consequences adopted
- Tiered profiles (Quick/Standard/Deep) with per-profile token budgets and input
  trimming (REQ-FR-001, REQ-COST-001).
- Structured debate + quality proxies (REQ-FR-003, REQ-QUAL-001).
- Deterministic rating authority + `REVIEW` (REQ-INV-003).
- Point-in-time withholding for live-only sources (REQ-INV-002).

## Part 6 / cost (2026-11-22)
- Actual code: runtime hard-stops over budget to `REVIEW`; summarize/cheaper-model
  routing implemented but not wired. Recorded so the requirement text matches
  reality (see REQ-COST-001 in `docs/req/requirements.yaml`).

## Verification evidence
- Regression suite and gate self-tests green on master (see CI); baseline in
  `docs/req/regression-baseline.json`.
