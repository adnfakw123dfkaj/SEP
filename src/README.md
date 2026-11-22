# src/ compatibility entry

D8 requires a top-level `src/` directory. This repository keeps the application
source in the existing package layout:

- `tradingagents/tradingagents/` — application package
- `tradingagents/cli/` — command-line surface

The root `src/` directory is a compatibility and review entry point. It does not
duplicate source files and is not on the Python import path. The authoritative
source remains `tradingagents/tradingagents/`.

Mapping:

| D8 path | Actual source |
|---|---|
| `src/` | `tradingagents/tradingagents/` and `tradingagents/cli/` |
| `test/offline/` | `tradingagents/tests/` with `-m "not integration"` |
| `test/live/` | `tradingagents/tests/` with `-m integration` |

If the course requires a physical `src/` tree instead of this compatibility
entry, the package and CLI must be migrated together with imports, packaging,
tests, and CI; that is tracked as a layout migration, not a documentation-only
change.
