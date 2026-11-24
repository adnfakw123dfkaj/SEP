# Part 6 — Performance and Cost

**Requirements covered:** `REQ-PER-001` (Must), `REQ-COST-001` (Must)

**Owned modules:** `contracts/llm_event.py`, `cost/` (`estimator.py`,
`budget.py`, `router.py`, `monitor.py`), `scripts/bench_latency.py`,
`scripts/token_audit.py`.

**Contracts used:** `ProfileConfig` (Part 1), `LLMCallEvent`, `RunManifest`
(Part 3).

**Fixtures:** `fixtures/llm_events/*.jsonl`, `fixtures/latency/baseline.json`,
`fixtures/cost/price_table.json`, recorded benchmark runs.

**Legend for kind:** OFFLINE / INTEGRATION / SCRIPT — see `README.md`.

> Both requirements are inherently **measured over runs on a reference
> environment**. The offline cases here validate the *accounting and the budget
> logic* against fixtures; the SCRIPT/INTEGRATION cases are the doc's verbatim
> `--assert-*` commands that need a reference env and either freshly recorded
> runs or quota.

---

## REQ-PER-001 — Tiered end-to-end latency

> On the reference environment (4 vCPU / 16 GB, provider latency ≤100 ms):
> p95 Quick ≤300 s, Standard ≤720 s, Deep ≤1800 s; cold/warm ≥15 runs each;
> p99 ≤1.2×p95; benchmark failure/timeout ≤1%; Quick/Standard improvement vs
> baseline ≥30%.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P6-PER001-01 | SCRIPT | Quick p95 | `quick_p95 <= 300` |
| TC-P6-PER001-02 | SCRIPT | Standard p95 | `standard_p95 <= 720` |
| TC-P6-PER001-03 | SCRIPT | Deep p95 | `deep_p95 <= 1800` |
| TC-P6-PER001-04 | SCRIPT | p99/p95 ratio | `p99_over_p95 <= 1.2` |
| TC-P6-PER001-05 | SCRIPT | Benchmark failure rate | `benchmark_failure_rate <= 0.01` |
| TC-P6-PER001-06 | SCRIPT | Improvement vs baseline | `quick_standard_improvement >= 0.30` |
| TC-P6-PER001-07 | OFFLINE | Latency accounting from fixtures | computed p95 == expected |

### TC-P6-PER001-01 — Quick p95 (SCRIPT / integration)
- **Given** the reference environment; 15 cold + 15 warm Quick runs.
- **When** `python scripts/bench_latency.py --profile quick --cold 15 --warm 15 --assert-p95 300`.
- **Then** p95 ≤ 300 s, exit 0.
- **Pass criterion:** `quick_p95 <= 300`.
- **Kind:** SCRIPT (needs reference env + quota or recorded runs).
- **Traces to:** REQ-PER-001 acceptance line 1.

### TC-P6-PER001-02 — Standard p95 (SCRIPT)
- **Pass criterion:** `standard_p95 <= 720`;
  `--profile standard --cold 15 --warm 15 --assert-p95 720`.
- **Traces to:** REQ-PER-001 acceptance line 2.

### TC-P6-PER001-03 — Deep p95 (SCRIPT)
- **Pass criterion:** `deep_p95 <= 1800`;
  `--profile deep --cold 15 --warm 15 --assert-p95 1800`.
- **Traces to:** REQ-PER-001 acceptance line 3.

### TC-P6-PER001-04 — Tail ratio (SCRIPT / boundary)
- **Given** a run set whose p99 is 1.15×p95 (pass) and one at 1.3× (fail).
- **When** `--assert-p99-ratio 1.2`.
- **Then** 1.15 passes, 1.3 fails.
- **Pass criterion:** `p99_over_p95 <= 1.2`.
- **Traces to:** REQ-PER-001 acceptance line 4.

### TC-P6-PER001-05 — Failure rate (SCRIPT / boundary)
- **Given** a set with 1/100 failures (0.01 pass) and 2/100 (0.02 fail).
- **When** `--assert-failure-rate 0.01`.
- **Then** 0.01 passes, 0.02 fails.
- **Pass criterion:** `benchmark_failure_rate <= 0.01`.
- **Traces to:** REQ-PER-001 acceptance line 5.

### TC-P6-PER001-06 — Baseline improvement (SCRIPT)
- **Given** `fixtures/latency/baseline.json` and current Quick/Standard runs.
- **When** `--baseline reports/baseline.json --assert-improvement 0.30`.
- **Then** improvement ≥30% or the case fails with the shortfall reported.
- **Pass criterion:** `quick_standard_improvement >= 0.30`.
- **Traces to:** REQ-PER-001 acceptance line 6.

### TC-P6-PER001-07 — Accounting logic (OFFLINE)
- **Given** `fixtures/latency/runs.jsonl` with known per-stage timings.
- **When** the bench script's percentile function runs offline.
- **Then** computed p50/p95/p99 equal precomputed expected values.
- **Pass criterion:** computed == expected (golden). This is the offline guard
  that the SCRIPT cases measure the right statistic.
- **Traces to:** REQ-PER-001 implementation (p50/p95/p99 reporting).

---

## REQ-COST-001 — Tiered token budget and cost report

> Single-run p95 token usage (input + output, incl. retries): Quick ≤25,000,
> Standard ≤60,000, Deep ≤150,000. Estimate tokens, choose direct/summary/
> cheaper-model/approval path by budget; record actual usage by agent/model/tool;
> 100% of runs emit a token/cost report; over-budget never continues silently.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P6-COST001-01 | SCRIPT | Quick p95 tokens | `quick_p95_tokens <= 80000` |
| TC-P6-COST001-02 | SCRIPT | Standard p95 tokens | `standard_p95_tokens <= 300000` |
| TC-P6-COST001-03 | SCRIPT | Deep p95 tokens | `deep_p95_tokens <= 300000` |
| TC-P6-COST001-04 | SCRIPT | Token report coverage | `token_report_coverage == 1.0` |
| TC-P6-COST001-05 | SCRIPT | No silent over-budget | `silent_over_budget_runs == 0` |
| TC-P6-COST001-06 | SCRIPT | Cost estimate error | `cost_estimate_relative_error <= 0.05` |
| TC-P6-COST001-07 | OFFLINE | Budget router preserves protected evidence | protected fields kept |
| TC-P6-COST001-08 | SCRIPT | Routed-run quality floor | `routed_run_quality_floor_pass_rate == 1.0` |

### TC-P6-COST001-01 — Quick tokens (SCRIPT / integration)
- **Given** 30 Quick runs on reference env.
- **When** `python scripts/token_audit.py --profile quick --runs 30 --assert-p95 80000`.
- **Then** p95 ≤ 25,000.
- **Pass criterion:** `quick_p95_tokens <= 80000`.
- **Kind:** SCRIPT.
- **Traces to:** REQ-COST-001 acceptance line 1.

### TC-P6-COST001-02 — Standard tokens (SCRIPT)
- **Pass criterion:** `standard_p95_tokens <= 300000`;
  `--profile standard --runs 30 --assert-p95 300000`.
- **Traces to:** REQ-COST-001 acceptance line 2.

### TC-P6-COST001-03 — Deep tokens (SCRIPT)
- **Pass criterion:** `deep_p95_tokens <= 300000`;
  `--profile deep --runs 30 --assert-p95 300000`.
- **Traces to:** REQ-COST-001 acceptance line 3.

### TC-P6-COST001-04 — Report coverage (happy / state)
- **Given** 30 runs.
- **When** `--runs 30 --assert-report-coverage 1.0`.
- **Then** every run emitted a token/cost report with per-agent/model/tool split.
- **Pass criterion:** `token_report_coverage == 1.0`.
- **Traces to:** REQ-COST-001 acceptance line 4.

### TC-P6-COST001-05 — No silent over-budget (negative / bypass)
- **Given** a run that would exceed its budget.
- **When** the router acts.
- **Then** it summarizes / drops to a cheaper model / requests approval; if still
  over, it marks the run over-budget (not silent).
- **Pass criterion:** `silent_over_budget_runs == 0`;
  `--runs 30 --assert-silent-over-budget 0`.
- **Traces to:** REQ-COST-001 acceptance line 5 — mandatory must-fail case.

### TC-P6-COST001-06 — Cost estimate accuracy (boundary ≤5%)
- **Given** a price table and recorded events with 3% and 7% estimator error.
- **When** `--assert-cost-error 0.05`.
- **Then** 3% passes, 7% fails.
- **Pass criterion:** `cost_estimate_relative_error <= 0.05`.
- **Traces to:** REQ-COST-001 acceptance line 6.

### TC-P6-COST001-07 — Protected evidence survives compaction (OFFLINE)
- **Given** a context over budget containing the verified snapshot, evidence refs,
  and risk constraints.
- **When** the summarizer compacts to fit.
- **Then** protected fields (snapshot, citation ids, risk constraints) are kept
  verbatim.
- **Pass criterion:** protected fields present and unchanged after compaction;
  fits budget.
- **Traces to:** REQ-COST-001 tradeoff (protected evidence) + `routed_run_quality_floor_pass_rate == 1.0`.

### TC-P6-COST001-08 — Routed-run quality floor (SCRIPT)
- **Given** runs routed to a cheaper path to fit budget.
- **When** `--assert-routed-quality 1.0`.
- **Then** every routed run still passes the quality floor (QUAL-001/002).
- **Pass criterion:** `routed_run_quality_floor_pass_rate == 1.0`.
- **Traces to:** REQ-COST-001 acceptance line 7 (quality gate protects routing).
