# Part 1 — Config, Profiles, and Input Gate

**Requirements covered:** `REQ-FR-001` (Must), `REQ-FR-002` (Should)

**Owned modules:** `tradingagents/profiles.py`, `contracts/profile.py`,
`preflight.py`, `default_config.py`, `cli/`; composition root
`graph/setup.py`, `graph/trading_graph.py`.

**Contracts used:** `ProfileConfig`, `PreflightResult`, `RunManifest` (read).

**Fixtures:** `fixtures/profiles/*.yaml`, `fixtures/preflight/*.json`.

**Legend for kind:** OFFLINE / INTEGRATION / SCRIPT — see `README.md`.

---

## REQ-FR-001 — Run profiles and reduced defaults

> System provides Quick / Standard / Deep profiles; each fixes analyst set,
> debate rounds, risk rounds, max tool rounds, model tiers, token budget,
> timeout, cache TTL. `--profile` overrides; manifest records profile and every
> override.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P1-FR001-01 | OFFLINE | Three preset profiles match the documented matrix | `profile_matrix_match_rate == 1.0` |
| TC-P1-FR001-02 | OFFLINE | Manifest records profile + overrides | `manifest_profile_coverage == 1.0` |
| TC-P1-FR001-03 | OFFLINE | Invalid override rejected before run | `invalid_profile_override_rejection_rate == 1.0` |
| TC-P1-FR001-04 | OFFLINE | `--profile` CLI flag selects the profile | selected profile == flag value |
| TC-P1-FR001-05 | OFFLINE | Default profile is Standard and applied when unset | `active_profile == "standard"` |
| TC-P1-FR001-06 | OFFLINE | Env override still wins over profile defaults | override value == env value |

### TC-P1-FR001-01 — Preset matrix (happy path + boundary)
- **Given** `profiles.py` exposes the three presets as `ProfileConfig`.
- **When** each preset is loaded and compared to `fixtures/profiles/expected_matrix.yaml`.
- **Then** every field matches: analyst set, `debate_rounds`, `risk_rounds`,
  `max_tool_rounds`, `quick_model`/`deep_model` tiers, `token_budget`,
  `timeout_s`, `cache_ttl`.
- **Pass criterion:** `profile_matrix_match_rate == 1.0`;
  `pytest tests/req/test_profiles.py::test_profile_matrix`.
- **Evidence:** the diff report the test prints on mismatch.
- **Traces to:** REQ-FR-001 acceptance line 1.

### TC-P1-FR001-02 — Manifest coverage
- **Given** a completed (or stubbed) run under each profile with one override.
- **When** `RunManifest` is written.
- **Then** `manifest.profile` equals the active profile and
  `manifest.overrides` lists every overridden key with its value.
- **Pass criterion:** `manifest_profile_coverage == 1.0`;
  `pytest tests/req/test_profiles.py::test_manifest_profile`.
- **Traces to:** REQ-FR-001 acceptance line 2.

### TC-P1-FR001-03 — Invalid override rejection (negative / bypass)
- **Given** `profile=quick` (which fixes a 1-analyst set).
- **When** the user forces `analysts=[market, social, news, fundamentals]` or a
  `max_tool_rounds` above the profile ceiling.
- **Then** the system **raises before any node runs** and the error names the
  conflicting field and the profile limit; no graph is built.
- **Pass criterion:** `invalid_profile_override_rejection_rate == 1.0`;
  `pytest tests/req/test_profiles.py::test_invalid_override`.
- **Traces to:** REQ-FR-001 acceptance line 3.

### TC-P1-FR001-04 — CLI selects the profile
- **Given** the Typer CLI.
- **When** invoked with `--profile deep`.
- **Then** the run config carries the Deep preset and the manifest records
  `profile="deep"`.
- **Pass criterion:** selected profile == `deep`; CLI test asserts no prompt is
  shown for the profile (non-interactive) and the config diff equals the preset.
- **Traces to:** REQ-FR-001 statement (`--profile` override).

### TC-P1-FR001-05 — Default when unset
- **Given** no `--profile` and no `run_profile` env var.
- **When** the config is built.
- **Then** the Standard preset applies.
- **Pass criterion:** `active_profile == "standard"`.
- **Traces to:** REQ-FR-001 reduction of defaults.

### TC-P1-FR001-06 — Env precedence over profile
- **Given** `TRADINGAGENTS_MAX_DEBATE_ROUNDS=5` set.
- **When** the Standard profile (which fixes a lower count) is built.
- **Then** the env value wins and is recorded as an override in the manifest.
- **Pass criterion:** `config["max_debate_rounds"] == 5` and
  `manifest.overrides` contains it.
- **Traces to:** REQ-FR-001 tradeoff (overrides recorded) + existing env-overlay rule.

---

## REQ-FR-002 — Preflight ticker and data availability

> Before the graph runs, verify the ticker resolves to a real instrument and
> core price data is available near the analysis date; on failure return a clear
> error and stop — no analysts, no LLM tokens.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P1-FR002-01 | OFFLINE | Invalid symbol → no analyst nodes called | analyst calls `== 0` |
| TC-P1-FR002-02 | OFFLINE | 50 valid tickers preflight pass | pass rate `== 1.0` |
| TC-P1-FR002-03 | OFFLINE | Preflight failure → 0 LLM tokens | token count `== 0` |
| TC-P1-FR002-04 | SCRIPT | Preflight p95 (cache hit) | p95 `<= 2s` |
| TC-P1-FR002-05 | OFFLINE | Data-unavailable distinguished from invalid | distinct `reason` values |
| TC-P1-FR002-06 | OFFLINE | Preflight result cached with TTLs | identity 7d / price 15m honored |

### TC-P1-FR002-01 — No analyst calls on invalid symbol (negative)
- **Given** `PreflightResult(resolved=False)` for symbol `NOTATICKER`.
- **When** the CLI runs the request.
- **Then** the graph is not entered; the run returns `invalid ticker`; the
  analyst-node call counter is zero.
- **Pass criterion:** analyst-node calls `== 0`;
  `pytest tests/req/test_preflight.py::test_no_analyst_calls`.
- **Traces to:** REQ-FR-002 acceptance line 1.

### TC-P1-FR002-02 — Valid ticker pass rate (happy)
- **Given** `fixtures/preflight/valid_tickers.json` (50 real symbols across
  markets: US, `.HK`, `.T`, crypto), each mapped to a recorded
  `PreflightResult`.
- **When** preflight runs offline against the fixtures.
- **Then** `resolved && tradable && data_available` for all 50.
- **Pass criterion:** pass rate `== 1.0`;
  `pytest tests/req/test_preflight.py::test_valid_tickers`.
- **Traces to:** REQ-FR-002 acceptance line 2.

### TC-P1-FR002-03 — Zero LLM tokens on failure (boundary)
- **Given** a failing preflight.
- **When** the request is rejected.
- **Then** the `LLMCallEvent` stream is empty for the run.
- **Pass criterion:** tokens `== 0`;
  `pytest tests/req/test_preflight.py::test_zero_llm_tokens`.
- **Traces to:** REQ-FR-002 acceptance line 3.

### TC-P1-FR002-04 — Preflight latency (SCRIPT)
- **Given** a warm 15-minute price cache.
- **When** `python scripts/bench_preflight.py --assert-p95 2` runs.
- **Then** cached-hit p95 ≤ 2 s and exit code 0.
- **Pass criterion:** p95 `<= 2s`.
- **Kind:** SCRIPT (needs the script plus fixtures; no live vendor when cache is
  pre-seeded).
- **Traces to:** REQ-FR-002 acceptance line 4.

### TC-P1-FR002-05 — Invalid vs unavailable (negative + boundary)
- **Given** two failing inputs: an unparseable symbol and a valid symbol whose
  recorded price window is stale/empty.
- **When** preflight runs.
- **Then** the first returns `reason="invalid ticker"`, the second
  `reason="data unavailable"`; the two reason strings differ and the second
  offers a retry hint.
- **Pass criterion:** both reasons present and distinct; test asserts the two
  `PreflightResult.reason` values.
- **Traces to:** REQ-FR-002 tradeoff (distinguish invalid / unavailable).

### TC-P1-FR002-06 — Cache TTL for preflight (state)
- **Given** a preflight that just resolved a ticker.
- **When** the same ticker is preflighted again 6 days later (identity) and 10
  minutes later (price).
- **Then** identity is served from cache (within 7 d), price is served from cache
  (within 15 m); past either boundary it re-queries.
- **Pass criterion:** cache-served flags match the TTL boundaries; a frozen-clock
  test.
- **Traces to:** REQ-FR-002 implementation plan (caching rules).
