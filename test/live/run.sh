#!/usr/bin/env bash
# D8 root wrapper: run the API-dependent live suite.
set -euo pipefail
cd "$(dirname "$0")/../../tradingagents"
exec ./test/live/run.sh "$@"
