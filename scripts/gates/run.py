"""Run one blocking gate as a CLI check.

Usage:
    python scripts/gates/run.py <gate> --input <json> [--warn-only]

``<gate>`` is ``g1``..``g7``. ``--input`` is a JSON file with the arguments for
that gate's ``check()``. ``--warn-only`` is layer 1 (branch self-check): report
violations but always exit 0. Without it, the run is layer 2 (PR to master) and a
failed gate exits non-zero.

The JSON printed to stdout is the machine report; the human summary goes to
stderr so stdout stays parseable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from check_ai_use_log import check as check_ai_use_log
from check_ownership import check as check_ownership
from check_regression import check as check_regression
from check_schema import check as check_schema
from check_semantic_eval import check as check_semantic_eval
from check_static_analysis import check as check_static_analysis
from check_test_approval import check as check_test_approval
from common import exit_code

_GATES = {
    "g1": (check_test_approval, ("changed_files", "approvals", "first_implementation_commit")),
    "g2": (check_static_analysis, ("changed_files", "check_results")),
    "g3": (check_schema, ("registry",)),
    "g4": (check_semantic_eval, ("changed_files", "metrics", "changed_config_keys")),
    "g5": (check_regression, ("baseline", "current", "approvals")),
    "g6": (check_ai_use_log, ("changed_files", "new_log_entries", "change_id")),
    "g7": (check_ownership, ("ownership", "outcomes")),
}


def main(argv: list[str]) -> int:
    warn_only = "--warn-only" in argv
    argv = [a for a in argv if a != "--warn-only"]
    if len(argv) < 2 or argv[0] not in _GATES:
        sys.stderr.write(__doc__ or "")
        return 2

    gate = argv[0]
    if "--input" not in argv or argv.index("--input") + 1 >= len(argv):
        sys.stderr.write("missing --input <json>\n")
        return 2
    input_path = argv[argv.index("--input") + 1]
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))

    func, keys = _GATES[gate]
    # Pass only the keys the caller provided; the check functions supply defaults
    # for optional inputs (e.g. G4's ``metrics``), so an omitted optional field
    # does not crash. A genuinely required field that is absent surfaces as an
    # error, which the workflow should never produce.
    kwargs = {k: payload[k] for k in keys if k in payload}
    result = func(**kwargs)

    print(json.dumps(result.to_dict(), indent=2))
    sys.stderr.write(result.render() + "\n")
    return exit_code(result, warn_only=warn_only)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
