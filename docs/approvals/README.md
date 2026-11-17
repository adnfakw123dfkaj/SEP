# Test-approval records (Gate 1)

Gate 1 blocks a code change unless its tests were approved **before**
implementation began. An approval is a committed JSON record here:

```json
{
  "change_id": "chg-2026-11-20-profiles",
  "tests": ["tradingagents/tests/req/test_profiles.py"],
  "approved_by": "alice",
  "approved_at": "2026-11-20T09:00:00+00:00"
}
```

Gate 1 checks: a record exists, its `tests` cover every changed test file, and
`approved_at` is earlier than the first non-test implementation commit in the PR.

## Deleting a test (Gate 5)

Tests may be modified or deleted by a branch. A **deletion** of a test that was
passing on `master` must be authorised here, or Gate 5 blocks the merge (a test
cannot be deleted to hide a red change). Add a `deletes` list to an approval:

```json
{
  "change_id": "chg-2026-11-20-drop-legacy",
  "deletes": ["tradingagents/tests/test_legacy_thing.py::test_old_behaviour"],
  "approved_by": "alice",
  "approved_at": "2026-11-20T09:00:00+00:00"
}
```

Any record with a `deletes` list is read by Gate 5; a missing previously-passing
test listed there is allowed, otherwise it blocks.

Name files `<change_id>.json`. `collect_context.py approvals` reads every
`*.json` here.
