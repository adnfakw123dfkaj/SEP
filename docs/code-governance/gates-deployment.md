# Blocking gates — deployment notes

How the six blocking gates (PDF §6, D7) are deployed on GitHub for this repo.

## Files

| File | Role |
|---|---|
| `.github/workflows/gates.yml` | Reusable workflow (`workflow_call`) — the **single set of gate rules**, owned by `master`. |
| `.github/workflows/ci.yml` | **Layer 2** entry: `pull_request → master`, calls `gates.yml` with `layer: blocking`. Plus the existing test/smoke/lint jobs and gate self-tests. |
| `.github/workflows/branch-check.yml` | **Layer 1** entry: thin stub on feature branches, calls `gates.yml@master` with `layer: warn-only`. |
| `scripts/gates/` | Gate decision logic (pure, pytest-verified) + `run.py` CLI + `collect_context.py`. |
| `tests/gates/` | Offline conformance tests for every gate. |
| `docs/req/requirements.yaml` + `req-schema.json` | Gate 3 registry + schema (14 requirements). |
| `docs/req/regression-baseline.json` | Gate 5 baseline of green `master` tests. |
| `docs/ai-use-log.yaml` | Gate 6 AI-use log (append-only). |
| `test-cases/ownership.yaml` | Gate 7 Part-ownership registry (manual claim; see `docs/gate-intro.md`). |
| `eval/fixed_set.py` + `eval/harness.py` | Gate 4 offline fixed evaluation set + harness. |
| `pyrightconfig.json` | Progressive type-checking (Gate 2): strict on `scripts/gates` + `eval`; legacy `tradingagents/` excluded. |

## Two layers

| Layer | Trigger | Rules | Code checked | Failure |
|---|---|---|---|---|
| 1 — branch self-check | push to a feature branch (`branch-check.yml`) | master (`gates.yml@master`, warn-only) | that branch | warns, never blocks |
| 2 — PR blocking | PR → master (`ci.yml`) | master (`gates.yml`, blocking) | PR head | blocks merge |

Both call the **same** `gates.yml`; only `layer` differs. Gate logic never lives
on a feature branch — the branch carries at most the thin `branch-check.yml` stub.

## Progressive type-checking (Gate 2)

The legacy `tradingagents/` package has ~313 pre-existing pyright errors, so
type-checking it strictly today would block every PR. Gate 2 therefore runs
pyright against `pyrightconfig.json`, which:

- **includes** `scripts/gates` and `eval` — our own safety-critical code — and
  checks them strictly (`basic` mode, errors on missing imports / unused names),
- **excludes** `tradingagents/`, `tests/`, caches.

`pyright` (run from the repo root) reports **0 errors** on the included zones. As
the package is progressively typed, add its directories to `include` and remove
them from `exclude`, one at a time. A deliberate type error in `scripts/gates` is
caught, so the gate enforces rather than passing vacuously.

CI note: the pip `pyright` package fetches a Node runtime on first invocation in
the runner; that is a one-time cost per job.


## Anti-bypass

On a `pull_request`, GitHub runs the workflow file from the **base** branch
(`master`) but checks out the **head** branch's code. Because the gate logic is
invoked by `master`'s `ci.yml` and `gates.yml`, a PR cannot replace the gate rules
it is checked against. (Hardening step, tracked in `test-cases/gates.md`
TC-G7-STRAT-05: also check out `master`'s `scripts/gates/` explicitly when
`pull_request_target` is adopted; the current `pull_request` model already runs
master's workflow definition.)

## Isolation

Every run (layer 1 and layer 2) runs on its own fresh runner, checks out only its
own ref, and writes only its own artifacts. No cache or state is shared across
branches.

## Branch protection (set in GitHub, not a file)

Set this as a **Ruleset** (Settings → Rules → Rulesets → New branch ruleset) on
`master`. Status checks only appear in the picker **after they have run once**, so
open one PR first (e.g. from `luochen`) to register them.

The `gates` job in `ci.yml` calls the reusable `gates.yml`, so GitHub reports each
gate as **`<caller> / <gate name>`**. With the explicit job names, the required
checks are:

- `gates / G1 test approval`
- `gates / G2 static analysis`
- `gates / G3 schema`
- `gates / G4 semantic eval`
- `gates / G5 regression`
- `gates / G6 AI-use log`
- `gates / G7 ownership`
- `gate self-tests`  (the standalone job that proves the gate logic)

Recommended ruleset settings:

- **Require a pull request before merging** (1 approval).
- **Require status checks to pass** → add the eight checks above; enable
  **Require branches to be up to date before merging**.
- **Block force pushes** and **restrict deletions**.
- For a change touching a safety-relevant path
  (`tradingagents/{agents,memory,dataflows,security,contracts,graph}/`, `scripts/gates/`),
  require a human review plus a linked architecture decision record.
- Changes to `.github/workflows/**` and `scripts/gates/**` require a gate-owner
  approval.
- Keep the `tests (py…)`, `ruff`, `clean-install smoke` matrix/standalone jobs
  **optional** — G5 already runs the full suite. (Each matrix cell is a separate
  check name like `tests (py3.12)`, so requiring "tests" would add four.)

## Regression baseline

`docs/req/regression-baseline.json` holds the green `master` snapshot Gate 5
compares against (1482 passing tests at recording time). It is keyed by
normalized node id: `tradingagents/tests/...` for the app suite (run from inside
`tradingagents/`) and `tests/gates/...` for the gate self-tests (run from the repo
root). Re-record it after an intentional change to the test set:

```bash
# from the repo root
( cd tradingagents && pip install pytest-json-report \
    && python -m pytest tests -q --json-report --json-report-file=/tmp/app.json ) || true
python -m pytest tests/gates -q --json-report --json-report-file=/tmp/gates.json || true
python - <<'PY'
import json
base = {f"tradingagents/{t['nodeid']}": t["outcome"]
        for t in json.load(open("/tmp/app.json"))["tests"] if t["outcome"] == "passed"}
for t in json.load(open("/tmp/gates.json"))["tests"]:
    if t["outcome"] == "passed":
        nid = t["nodeid"]; i = nid.find("tests/gates/")
        base[nid[i:] if i >= 0 else nid] = "passed"
json.dump(base, open("docs/req/regression-baseline.json", "w"), indent=2, sort_keys=True)
PY
```

## First-time setup

1. The baseline is already recorded; re-record it only after a deliberate
   test-set change (see above). Branches may edit or delete tests freely; a
   deletion of a previously-passing test needs an approval record listing it under
   `deletes` (Gate 5), or the merge is blocked.
2. Add `docs/approvals/<change_id>.json` records for changes that add tests or
   delete previously-passing tests.
3. Copy `branch-check.yml` onto feature branches that want early self-checks.
4. Configure branch protection as above.
