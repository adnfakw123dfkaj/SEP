#!/usr/bin/env bash
# D8 offline test entry: deterministic, no network.
set -euo pipefail
cd "$(dirname "$0")/../.."   # tradingagents/ project dir
exec python -m pytest tests -q -m "not integration" "$@"
