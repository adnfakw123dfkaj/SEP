# Test-Case Specification — Conventions

This folder specifies the test cases for the 14 requirements in
`requirements-final.md`. It is a **specification**, not runnable code: the
subject modules (`profiles.py`, `contracts/`, `security/`, `cost/`, `tests/req/`,
the scripts) do not exist yet. Each case states exactly what to build so that an
implementer can turn it into a `pytest` test or script invocation without
re-deciding intent.

The folder is intentionally outside the `tradingagents/` package so it is never
collected by the application's `pytest` run.

## Files

| File | Part | Requirements |
|---|---|---|
| `part1-profiles-preflight.md` | 1 — Config, profiles, input gate | `REQ-FR-001`, `REQ-FR-002` |
| `part2-debate.md` | 2 — Structured debate | `REQ-FR-003`, `REQ-QUAL-001` |
| `part3-evidence-records.md` | 3 — Evidence, report, records | `REQ-FR-004`, `REQ-QUAL-002`, `REQ-INV-001` |
| `part4-resilience-pit.md` | 4 — Resilience & point-in-time | `REQ-FR-005`, `REQ-INV-002` |
| `part5-security-rating.md` | 5 — Security & rating authority | `REQ-INV-003`, `REQ-SEC-001`, `REQ-INV-004` |
| `part6-perf-cost.md` | 6 — Performance & cost | `REQ-PER-001`, `REQ-COST-001` |

---

## Test-case ID scheme

`TC-P<part>-<reqshort>-<nn>`

- `P<part>` — Part number (1–6).
- `<reqshort>` — requirement without the `REQ-` prefix and hyphen, e.g. `FR001`,
  `INV001`, `QUAL002`, `SEC001`.
- `<nn>` — two-digit sequence within the requirement.

Example: `TC-P3-INV001-02` is the second case for Part 3, `REQ-INV-001`.

Each case has a **kind**:

| Kind | Meaning | Runs in CI? |
|---|---|---|
| **OFFLINE** | Deterministic; uses fixtures/synthetic input; no network, no LLM. | Yes, always. |
| **INTEGRATION** | Needs the real graph / live provider / N captured runs. | Only with fixtures or quota; marked `integration`. |
| **SCRIPT** | Invoked as a command-line script with `--assert-*` flags (e.g. `bench_latency.py`). | Via the script's own gate. |

## Case anatomy (standard)

Every case is written as a table row plus a detail block with these fields:

- **Given** — preconditions, fixtures, and the exact subject under test.
- **When** — the action / input.
- **Then** — the expected observable result.
- **Pass criterion** — the machine-decidable rule (metric + threshold + the
  exact command from the requirement's fit criterion where one exists).
- **Evidence** — the artifact produced (log, JSON, report path).
- **Fixtures** — which fixture files the case needs (see inventory).
- **Traces to** — the requirement fit-criterion line it verifies.

## Required case types per requirement

To keep coverage honest, every requirement must have, at minimum:

1. **Happy path** — the normal success case.
2. **Boundary** — exactly at the threshold.
3. **Negative / bypass** — a case that *must fail* (the gate must catch it).
4. **Determinism / idempotency** — where the requirement claims it (e.g. the
   invariants), a repeat-run or reorder case.

The **bypass case is mandatory**: a requirement with no must-fail case is not
considered covered.

## Offline vs integration strategy

`requirements-final.md` fit criteria lean on "30 transcripts", "15 cold + 15
warm runs", "30 reports", "200 + 200 injections". Those cannot run in offline
CI. The strategy, used consistently in every Part file:

- **OFFLINE cases** assert the *logic* against **recorded fixtures**:
  - transcripts under `test-cases/fixtures/transcripts/*.json`
  - reports under `test-cases/fixtures/reports/*.md`
  - manifests under `test-cases/fixtures/manifests/*.json`
  - provider event streams under `test-cases/fixtures/llm_events/*.jsonl`
  - injection payloads under `test-cases/fixtures/security/{injections,benign}.txt`
- **INTEGRATION cases** are the requirement's verbatim command (e.g.
  `--runs 30`) and are marked `integration`; CI runs them nightly with quota or
  against freshly recorded fixtures. They never block the fast offline suite.

A case that *could* be either is specified as OFFLINE with a recorded fixture,
and the matching INTEGRATION case is listed separately, so the offline CI proves
the check and the integration run proves it on live data.

Even offline, the application's autouse `_no_network` fixture (see
`tradingagents/tests/conftest.py`) blocks sockets, so offline cases must not try
to reach a vendor; they read fixtures.

## Fixture inventory (to be created alongside the subject code)

| Fixture dir | Consumer | Shape |
|---|---|---|
| `fixtures/profiles/*.yaml` | Part 1 | Profile presets + expected matrices |
| `fixtures/preflight/*.json` | Part 1 | ticker → resolved/tradable/data_available |
| `fixtures/transcripts/*.json` | Part 2 | Structured debate turns, golden + adversarial |
| `fixtures/reports/*.md` | Part 3 | Reports with/without evidence refs, numeric claims |
| `fixtures/manifests/*.json` | Part 3 | Valid/invalid RunManifest samples |
| `fixtures/llm_events/*.jsonl` | Parts 3, 6 | `LLMCallEvent` streams with usage |
| `fixtures/cache/*` | Part 4 | Pre-seeded caches with TTL/provenance |
| `fixtures/point_in_time/*.json` | Part 4 | Items straddling the analysis date |
| `fixtures/security/injections.txt` | Part 5 | ≥200 injection payloads |
| `fixtures/security/benign.txt` | Part 5 | ≥200 benign texts |
| `fixtures/security/secrets.txt` | Part 5 | Synthetic keys/tokens to redact |
| `fixtures/latency/baseline.json` | Part 6 | Stage timings for the baseline comparison |

Fixture files are recorded once, committed, and versioned with the test spec.

## Traceability matrix

| Req | Priority | Cases | File |
|---|---|---|---|
| `REQ-FR-001` | Must | TC-P1-FR001-01..06 (6) | part1 |
| `REQ-FR-002` | Should | TC-P1-FR002-01..06 (6) | part1 |
| `REQ-FR-003` | Must | TC-P2-FR003-01..06 (6) | part2 |
| `REQ-QUAL-001` | Must | TC-P2-QUAL001-01..06 (6) | part2 |
| `REQ-FR-004` | Must | TC-P3-FR004-01..06 (6) | part3 |
| `REQ-QUAL-002` | Should | TC-P3-QUAL002-01..06 (6) | part3 |
| `REQ-INV-001` | Should | TC-P3-INV001-01..06 (6) | part3 |
| `REQ-FR-005` | Must | TC-P4-FR005-01..07 (7) | part4 |
| `REQ-INV-002` | Should | TC-P4-INV002-01..06 (6) | part4 |
| `REQ-INV-003` | Must | TC-P5-INV003-01..07 (7) | part5 |
| `REQ-SEC-001` | Must | TC-P5-SEC001-01..07 (7) | part5 |
| `REQ-INV-004` | Must | TC-P5-INV004-01..06 (6) | part5 |
| `REQ-PER-001` | Must | TC-P6-PER001-01..07 (7) | part6 |
| `REQ-COST-001` | Must | TC-P6-COST001-01..08 (8) | part6 |

Total: 14 requirements, 90 test cases.

## Conventions shared by all cases

- **No real money, no real orders** — the system already is advisory only; tests
  never assert execution.
- **Time is pinned.** Every case that involves "today" sets a frozen date via the
  existing `get_current_date` seam or a fixture clock, so `is_historical`
  branches are deterministic.
- **Counts are exact where the invariant demands zero** (e.g.
  `future_dated_items_in_prompt == 0`), and rate-based where the requirement
  states a rate (e.g. `citation_support_rate >= 0.95`).
- **Evidence paths** are relative to the run's `results_dir`; a case records the
  path it inspects so the evidence is reproducible.
- **Skip conditions** are explicit: an INTEGRATION case that lacks quota or
  fresh fixtures is skipped with a reason, never silently passed.
