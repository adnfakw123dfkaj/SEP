# Phase 1 Current Status Report

Date: 2026-11-22  
Branch: `master`  
Latest commit before this report: `58a8510 Optimize profile prompt and tool budgets`

## 1. Purpose

This document summarizes the current implementation state for review by the other
team members before the final acceptance work continues.

The current goal is to make the six-part integration runnable, auditable, and
measurable. It is not yet the final performance-acceptance state.

## 2. Completed Work

### 2.1 Six-part integration

Part 1-6 are wired into the same execution path:

- Part 1: named profiles, Standard default for headless runs, preflight, cache TTL
- Part 2: structured debate, transcript persistence, debate quality metrics
- Part 3: manifest, evidence registry, claim-level evidence, state log, records
- Part 4: checkpoint, cache, fallback, vendor/PIT/cache/resume/fallback metrics
- Part 5: rating authority, sanitization, tool guard, output validation, redaction
- Part 6: cost tracking, budget hard fail, quality floor, benchmark CLIs

### 2.2 Real live runs

Quick, Standard, and Deep have all completed real DeepSeek API runs.

Live artifacts include:

- manifest
- full state log
- debate transcript
- evidence index
- claim evidence
- rating records
- report tree
- cost report
- security events
- fallback events

### 2.3 Safety and correctness

Verified behavior:

- pre-call budget hard fail
- REVIEW result and exit code 2 on over-budget runs
- BudgetExceededError is not swallowed by LangChain callbacks
- evidence capture works on the CLI stream path
- Part 5 rating authority is committed
- full state log includes cost, evidence, output validation, and rating authority
- Windows headless UTF-8 output works
- cache file locking works under parallel analysts
- verified market snapshot is captured even if the model skips the tool

### 2.4 Cost and quality gates

Implemented:

- independent provider-usage cost ground truth
- composite quality floor:
  - Part 2 debate quality
  - Part 3 report schema and citation support
  - Part 3 claim evidence coverage
  - Part 3 numeric contradiction
  - Part 5 output validation and rating authority
- claim-level evidence mapping:
  - `claim_id -> evidence_refs -> snapshot_hashes`
- quality floor pass rate in token audits

### 2.5 Part 4 metrics

Manifest and state log record:

- real vendor versions
- PIT coverage
- cache hits, misses, writes, skipped writes, stale reads, hit rate
- resume enabled/resumed
- fallback counts by kind/source/action

## 3. Performance Status

### Unoptimized baseline

These are single-run pilots, not formal 15-run benchmarks.

| Profile | Tokens | Cost CNY |
|---|---:|---:|
| Quick | 182,364 | 0.475710 |
| Standard | 289,282 | 0.615950 |
| Deep | 443,673 | 0.860351 |

### First optimization pass

| Profile | Optimized tokens | Reduction | Cost CNY | Target |
|---|---:|---:|---:|---:|
| Quick | 77,190 | 57.7% | 0.279691 | 25,000 |
| Standard | 147,239 | 49.1% | 0.447714 | 60,000 |
| Deep | 282,812 | 36.3% | 0.727994 | 150,000 |

Current gaps:

- Quick: 3.09x over target
- Standard: 2.45x over target
- Deep: 1.89x over target

Quality floor passed for Quick and Deep. Standard's first stored result hit a
numeric false positive; the same saved state passed after the parser fix.

## 4. Optimization Already Applied

- Quick/Standard/Deep tool-round limits tightened
- profile-specific tool-output truncation
- profile-specific report-prompt truncation
- profile-specific model output caps
- verified snapshot capture moved outside model control
- historical/window numeric false positives filtered
- agent attribution fixed for wrapped analyst turns

## 5. Remaining Work

### P0

1. Second optimization pass:
   - debate/risk history compression
   - downstream report-context compression
   - optional Part 6 context summarization

2. Formal benchmark:
   - Quick/Standard/Deep
   - cold and warm runs
   - 15 samples per profile
   - p50/p95/p99, failures, cost, quality

### P1

3. Final acceptance:
   - token caps
   - quality floor
   - cost ground truth
   - cache/resume/fallback metrics

4. Re-run G1-G7 on the final code state.

5. Update approvals, AI-use log, ownership, and final session record.

### Known limitations

- claim evidence attribution is block/section level, not full semantic entailment
- numeric contradiction only covers labelled market values in the final decision
- PIT coverage is a policy-level map, not a source-by-source audit
- custom HTTP vendor versions use `tradingagents-<version>`
- warm cache hit rate has not yet been formally benchmarked
- FRED key and Reddit endpoint data gaps remain environment limitations

## 6. Gate and Push Status

Local G1-G7 results on the code state before this documentation commit:

```text
G1 pass
G2 pass
G3 pass
G4 pass
G5 pass
G6 pass
G7 pass
```

Notes:

- G1 uses the combined-integration approval in
  `docs/approvals/phase1-final-integration.json`. The approval timestamp follows
  the previously authorized G1 backfill policy for the combined integration
  change.
- G5 ran the full application suite plus the gate self-tests.
- G6 sees the new `phase1-final-integration` entry in `docs/ai-use-log.yaml`.
- This report and the approval/log updates are included in the same push.

The branch is pushed only after these local gates pass.

## 7. Reproduce

From the repository root:

```powershell
python scripts/gates/collect_context.py changed --base origin/master
python scripts/gates/run.py g1 --input <g1.json>
python scripts/gates/run.py g2 --input <g2.json>
python scripts/gates/run.py g3 --input <g3.json>
python scripts/gates/run.py g4 --input <g4.json>
python scripts/gates/run.py g5 --input <g5.json>
python scripts/gates/run.py g6 --input <g6.json>
python scripts/gates/run.py g7 --input <g7.json>
```

Full application suite:

```powershell
cd tradingagents
python -m pytest -q
```
