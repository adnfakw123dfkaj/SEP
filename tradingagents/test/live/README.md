# Live tests (D8)

API-dependent tests, marked `integration`. They are excluded from the default and
offline runs and only execute when asked for. They need real provider keys / quota
and network access.

Run from the `tradingagents/` project directory:

    python -m pytest tests -q -m integration

To list them without running:

    python -m pytest tests -m integration --co -q

Live tests are not part of the blocking CI path; they are run on demand.

## What runs live (new requirements)

`tests/req/test_live_end_to_end.py` runs the real pipeline once (quick profile,
one analyst) and asserts the artifacts the new requirements demand from an actual
run:

- REQ-FR-004 — evidence refs + `manifest.json` written on disk
- REQ-QUAL-002 — report sections + citation support on the produced report
- REQ-COST-001 — `cost_report` present; over-budget is explicit (never silent)
- REQ-INV-003 — committed rating in the closed set (or REVIEW)
- REQ-INV-002 — a historical run carries no data dated after its trade_date

Plus the pre-existing live tests: debate schema (REQ-FR-003), debate quality
(REQ-QUAL-001), and tiered latency (REQ-PER-001). All are skipped without a
provider key.
