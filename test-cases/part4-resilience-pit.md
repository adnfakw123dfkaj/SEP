# Part 4 — Data Resilience and Point-in-Time Integrity

**Requirements covered:** `REQ-FR-005` (Must), `REQ-INV-002` (Should)

**Owned modules:** `contracts/cache.py`, `cache/`, `resilience.py`,
`graph/checkpointer.py`, `dataflows/date_window.py`.

**Contracts used:** `ProfileConfig` (Part 1), `CacheKey`/TTL, `RunManifest`
(Part 3), `LLMCallEvent` (Part 6).

**Fixtures:** `fixtures/cache/*`, `fixtures/point_in_time/*.json`,
`fixtures/llm_events/*.jsonl`, recorded OHLCV/news snapshots.

**Legend for kind:** OFFLINE / INTEGRATION / SCRIPT — see `README.md`.

---

## REQ-FR-005 — Cache, checkpoint, and degradation

> Standard/Deep enable node checkpoints; on interrupt resume from the last
> successful node with no duplicate LLM calls for completed nodes. Data is
> cached per data class with a TTL and provenance; when a source is unavailable,
> use unexpired cache, else mark `<unavailable>` and lower confidence — never
> fabricate. On LLM failure, bounded retry, then degrade to a cheaper model or
> return `REVIEW`.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P4-FR005-01 | OFFLINE | Resume reuses completed nodes | `resume_reuse_rate >= 0.90` |
| TC-P4-FR005-02 | OFFLINE | No duplicate LLM calls on resume | `duplicate_completed_node_llm_calls == 0` |
| TC-P4-FR005-03 | OFFLINE | Cache hit rate within TTL | `cache_hit_rate >= 0.70` |
| TC-P4-FR005-04 | OFFLINE | No stale cache use | `stale_cache_use_count == 0` |
| TC-P4-FR005-05 | OFFLINE | No fabricated data on source failure | `fabricated_data_placeholder_count == 0` |
| TC-P4-FR005-06 | OFFLINE | Typed fallback events recorded | `typed_fallback_event_coverage == 1.0` |
| TC-P4-FR005-07 | OFFLINE | LLM failure → retry → degrade/REVIEW | path recorded, no silent continue |

### TC-P4-FR005-01 — Resume reuse (happy)
- **Given** a run checkpointed to node k, then interrupted.
- **When** resumed.
- **Then** nodes 1..k are not recomputed; execution continues from k+1.
- **Pass criterion:** `resume_reuse_rate >= 0.90`;
  `pytest tests/req/test_checkpoint_resume.py::test_resume`.
- **Traces to:** REQ-FR-005 acceptance line 1.

### TC-P4-FR005-02 — No duplicate calls (determinism)
- **Given** the same interrupted run and its `LLMCallEvent` stream.
- **When** resumed.
- **Then** no completed node emits a second LLM call.
- **Pass criterion:** `duplicate_completed_node_llm_calls == 0`;
  `pytest tests/req/test_checkpoint_resume.py::test_no_duplicate_calls`.
- **Traces to:** REQ-FR-005 acceptance line 2.

### TC-P4-FR005-03 — Cache hit rate (boundary 0.70)
- **Given** a pre-seeded cache and a sequence of repeated data requests within
  TTL: 7/10 and 6/10 hit.
- **When** served.
- **Then** 0.70 passes, 0.60 fails.
- **Pass criterion:** `cache_hit_rate >= 0.70`;
  `pytest tests/req/test_cache.py::test_hit_rate`.
- **Traces to:** REQ-FR-005 acceptance line 3.

### TC-P4-FR005-04 — No stale cache (negative)
- **Given** a cache entry past its data-class TTL.
- **When** a request arrives.
- **Then** it is not served; it re-fetches (or marks unavailable), never uses
  the expired value.
- **Pass criterion:** `stale_cache_use_count == 0`;
  `pytest tests/req/test_cache.py::test_no_stale`.
- **Traces to:** REQ-FR-005 acceptance line 4.

### TC-P4-FR005-05 — No fabrication (negative / bypass)
- **Given** a vendor that fails and an empty cache.
- **When** the fallback chain runs.
- **Then** the value becomes `<unavailable>` with lowered confidence; no
  invented number appears.
- **Pass criterion:** `fabricated_data_placeholder_count == 0`;
  `pytest tests/req/test_fallback.py::test_no_fabrication`.
- **Traces to:** REQ-FR-005 acceptance line 5 — mandatory must-fail case.

### TC-P4-FR005-06 — Typed events (state)
- **Given** each degradation path (retry, cache-fallback, unavailable, REVIEW).
- **When** triggered.
- **Then** a typed `fallback_event` is written to the manifest.
- **Pass criterion:** `typed_fallback_event_coverage == 1.0`;
  `pytest tests/req/test_fallback.py::test_typed_events`.
- **Traces to:** REQ-FR-005 acceptance line 6.

### TC-P4-FR005-07 — LLM failure degrade (negative)
- **Given** a provider that always errors.
- **When** the resilience chain runs.
- **Then** it retries a bounded number of times, then degrades to a cheaper
  model; if that also fails, the rating becomes `REVIEW` (never a silent Hold).
- **Pass criterion:** retry count bounded; final state == `REVIEW`; a typed
  event recorded; no silent continue.
- **Traces to:** REQ-FR-005 statement (degradation) — must-fail case.

---

## REQ-INV-002 — Point-in-time integrity (no look-ahead)

> No data item dated after the analysis date enters any agent input: price,
> indicators, news, fundamentals, insider, social, memory lessons. Undated items
> are dropped in historical windows; social sources return "unavailable" for
> historical runs rather than live posts.

### Case index

| ID | Kind | Title | Pass criterion |
|---|---|---|---|
| TC-P4-INV002-01 | OFFLINE | No future-dated items in prompt | `future_dated_items_in_prompt == 0` |
| TC-P4-INV002-02 | OFFLINE | Every dated tool has a PIT test | tool coverage `== 1.0` |
| TC-P4-INV002-03 | OFFLINE | Social unavailable on historical run | unavailable rate `== 1.0` |
| TC-P4-INV002-04 | OFFLINE | Property test over 100 historical dates | pass rate `== 1.0` |
| TC-P4-INV002-05 | OFFLINE | Undated item dropped in historical window | 0 undated kept |
| TC-P4-INV002-06 | OFFLINE | Memory lessons filtered by resolution date | 0 future lessons |

### TC-P4-INV002-01 — No future items (negative / core)
- **Given** fixtures injecting items dated analysis+1 day into each path.
- **When** the prompt is assembled for a historical date.
- **Then** none of the future items appear.
- **Pass criterion:** `future_dated_items_in_prompt == 0`;
  `pytest tests/req/test_point_in_time.py::test_no_future_items`.
- **Traces to:** REQ-INV-002 acceptance line 1 — mandatory must-fail case.

### TC-P4-INV002-02 — Tool coverage (state)
- **Given** the inventory of dated tools (prices, indicators, news, global news,
  fundamentals, statements, insider, macro, prediction markets, social).
- **When** the PIT test registry is checked.
- **Then** every dated tool maps to a PIT test.
- **Pass criterion:** tool coverage `== 1.0`;
  `pytest tests/req/test_point_in_time.py::test_tool_coverage`.
- **Traces to:** REQ-INV-002 acceptance line 2.

### TC-P4-INV002-03 — Social unavailable historically (boundary)
- **Given** a historical analysis date for a ticker with social sources.
- **When** the sentiment path runs.
- **Then** the social block reads `<unavailable>`, not live posts.
- **Pass criterion:** unavailable rate `== 1.0`;
  `pytest tests/req/test_point_in_time.py::test_social_unavailable`.
- **Traces to:** REQ-INV-002 acceptance line 3.

### TC-P4-INV002-04 — Property over dates (determinism)
- **Given** 100 historical dates and randomly dated items straddling each.
- **When** the property check runs.
- **Then** no post-date item leaks for any date.
- **Pass criterion:** pass rate `== 1.0`;
  `pytest tests/req/test_point_in_time.py::test_property_dates`.
- **Traces to:** REQ-INV-002 acceptance line 4.

### TC-P4-INV002-05 — Undated item dropped (boundary)
- **Given** a news item with no timestamp in a historical window.
- **When** the window filter runs.
- **Then** the undated item is dropped (cannot prove it is not from the future).
- **Pass criterion:** 0 undated items kept when the window does not reach now.
- **Traces to:** REQ-INV-002 statement (undated dropped).

### TC-P4-INV002-06 — Memory lessons filter (state)
- **Given** a memory log whose lessons resolve after a historical analysis date.
- **When** past context is injected for that date.
- **Then** only lessons resolved on/before the date are included.
- **Pass criterion:** 0 future lessons injected.
- **Traces to:** REQ-INV-002 statement (memory lessons) + existing `as_of` filter.
