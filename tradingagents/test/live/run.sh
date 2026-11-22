#!/usr/bin/env bash
# D8 live test entry: API-dependent (marked integration).
set -euo pipefail
cd "$(dirname "$0")/../.."   # tradingagents/ project dir
exec python -m pytest tests -q -m integration "$@"
