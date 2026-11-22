# Live tests (D8)

This is the root-level D8 entry point for API-dependent tests. It delegates to
the existing integration-marked suite in `tradingagents/tests/` and requires
provider credentials and network access.

Run from the repository root:

```bash
./test/live/run.sh
```

The authoritative implementation remains:

```text
tradingagents/test/live/run.sh
```
