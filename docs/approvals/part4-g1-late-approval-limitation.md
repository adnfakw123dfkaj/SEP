# Part 4 G1 late-approval limitation

Part 4 was implemented before this integration approval was recorded.

- Implementation commit: `25b2414` (`Implement Part 4 resilience`)
- Implementation timestamp: `2026-11-21T17:15:37+08:00`
- Approval record: `docs/approvals/part4-resilience.json`
- Approval timestamp: `2026-11-21T17:46:41+08:00`

Gate G1 requires test approval before the first non-test implementation commit.
That ordering is not satisfied for Part 4. The approval file covers the changed
test files, but it is an integration-time approval, not evidence of prior
approval.

This limitation is recorded deliberately. The timestamps were not backdated.
G1 should remain blocked for Part 4 unless the gate owner explicitly accepts an
exception or the work is re-run through an approval-first flow.
