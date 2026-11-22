# Offline tests (D8)

This is the root-level D8 entry point. It delegates to the existing deterministic
offline suite in `tradingagents/tests/`; no network or live API is used.

Run from the repository root:

```bash
./test/offline/run.sh
```

The authoritative implementation remains:

```text
tradingagents/test/offline/run.sh
```
