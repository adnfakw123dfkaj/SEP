# Part 5 — G1 governance evidence & multi-round limitation

Status: **governance evidence complete; current G1 check FAILS on this branch.**
Both facts are reported separately. No gate code was edited, no approval
timestamp was back-dated, no record was hidden.

## Approvals on this branch (real, restored verbatim from git history)

Files (both restored byte-for-byte from the commits that introduced them, not
re-typed):

1. `docs/approvals/chg-2026-11-18-part5-security-rating.json`
   - `approved_by`: 陈妍妍
   - `approved_at`: **2026-11-18T06:43:59+00:00**
   - Introduced in commit `767c486` (approve + claim), **before** any Part 5
     implementation commit.
   - `tests` covered: the three Part 5 test files + `injections.txt`,
     `benign.txt`, `secrets.txt`.

2. `docs/approvals/chg-2026-11-18-part5-acceptance-2.json`
   - `approved_by`: 陈妍妍
   - `approved_at`: **2026-11-18T07:36:35+00:00**
   - Introduced in commit `a54040e`, before the round-2 implementation commit
     `bc1929c`.
   - `tests` covered: the three Part 5 test files + fixtures **including the new
     `injections.expected.jsonl`**.

Both timestamps are genuine (taken from the system clock at write time on the
round they belong to); neither is back-dated.

## What each approval covers

| Round | Approval | Covers |
|---|---|---|
| Round 1 (initial implementation) | `06:43:59Z` | 3 test files + 3 fixtures (no `.expected.jsonl`) |
| Round 2 (review fixes) | `07:36:35Z` | 3 test files + 4 fixtures (incl. `.expected.jsonl`) |

The reviewer approved each round's scenarios in-session before that round's code,
as recorded in the exported session (`docs/part5-session/README.md`, human-index
rows 2 and 5).

## Why the current G1 check FAILS (and why it cannot express multi-round approval)

`scripts/gates/check_test_approval.py` (unmodified) behaves as follows:

1. It receives **one** `first_implementation_commit` = the PR's *earliest*
   non-test code commit (`collect_context.py first-impl-commit`). Here that is
   `0e5e31d` at `2026-11-18T15:00:39+08:00` = `07:00:39Z` (round 1).
2. It loops over approvals; for each, it requires the approval to cover **every**
   changed test file and to have `approved_at < impl_time`.
3. It **appends violations for failing approvals and keeps going**; it only
   returns a clean result if some approval passes both checks. Violations from an
   earlier-loop failing approval remain in the result even if a later approval
   passes.

Consequences on this branch:

- Round-1 approval (`06:43:59Z`) predates impl and would pass ordering, but it
  does **not** list the round-2 fixture `injections.expected.jsonl`, so the
  "approval does not cover changed tests" check fails for it.
- Round-2 approval (`07:36:35Z`) covers all changed tests, but it was written
  *after* the round-1 implementation time, so `07:36:35Z >= 07:00:39Z` triggers
  "approval after implementation".

So **no single approval** can satisfy both "covers all changed tests" and
"predates the earliest implementation" for a change that legitimately has more
than one review round. The gate has no concept of per-round implementation start
times or of an approval that supersedes an earlier one for a later round.

### Exact current result

```
gate G1: fail
  - approval after implementation: approved 2026-11-18T07:36:35+00:00 >= implementation 2026-11-18T15:00:39+08:00
  - approval does not cover changed tests: tradingagents/tests/fixtures/security/injections.expected.jsonl
```

This is reported truthfully. It is **not** worked around (no deleted approval, no
re-typed timestamp, no gate edit, no expanded ignore).

## Handoff to the gate owners

Suggested options for the G1 owner (this Part does not implement them):

- Accept a DAG of changes each with its own first-implementation time, evaluating
  each approval against the first implementation commit of the change it covers.
- Or compare `approved_at` against the first implementation commit of the
  *specific test files* the approval lists, rather than one PR-wide earliest time.
- Or stop accumulating violations from a failing approval once a later approval
  satisfies the whole change.

Until resolved, the machine gate will block on G1 even though the human approvals
are real, complete, and correctly ordered per round.

## Separation of reports

- **Governance evidence completeness:** complete. Real, non-back-dated approvals
  for both rounds exist and are preserved; the human decisions are in the exported
  session.
- **Current machine gate (G1):** **fails**, for the structural reason above.
  Handed to the gate owner; not bypassed.
