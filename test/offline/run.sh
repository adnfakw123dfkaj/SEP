#!/usr/bin/env bash
# D8 root wrapper: run the deterministic offline suite.
set -euo pipefail
cd "$(dirname "$0")/../../tradingagents"
exec ./test/offline/run.sh "$@"
