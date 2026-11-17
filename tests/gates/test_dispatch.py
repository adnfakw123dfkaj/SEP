import json
import subprocess
import sys
from pathlib import Path

import common

GATES_DIR = Path(__file__).resolve().parents[2] / "scripts" / "gates"


def test_exit_code_warn_only_never_fails():
    result = common.GateResult(gate="G5")
    result.violations.append(common.Violation("x"))
    assert common.exit_code(result, warn_only=True) == 0


def test_exit_code_blocking_fails_on_violation():
    result = common.GateResult(gate="G5")
    result.violations.append(common.Violation("x"))
    assert common.exit_code(result, warn_only=False) == 1


def test_exit_code_pass_is_zero_either_way():
    result = common.GateResult(gate="G5")
    assert common.exit_code(result, warn_only=False) == 0
    assert common.exit_code(result, warn_only=True) == 0


def _run_gate(tmp_path, gate, payload, warn_only=False):
    input_path = tmp_path / "in.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    argv = [sys.executable, str(GATES_DIR / "run.py"), gate, "--input", str(input_path)]
    if warn_only:
        argv.append("--warn-only")
    return subprocess.run(argv, capture_output=True, text=True, cwd=str(GATES_DIR))


def test_cli_blocks_failing_gate(tmp_path):
    payload = {
        "baseline": {"t": "passed"},
        "current": {"t": "failed"},
    }
    proc = _run_gate(tmp_path, "g5", payload)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"


def test_cli_warn_only_passes_exit_but_reports(tmp_path):
    payload = {"baseline": {"t": "passed"}, "current": {"t": "failed"}}
    proc = _run_gate(tmp_path, "g5", payload, warn_only=True)
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"


def test_cli_g4_without_metrics_key_does_not_crash(tmp_path):
    # A non-eval change: the workflow omits "metrics". run.py must not pass a
    # missing required arg; G4 defaults it and reports skipped.
    payload = {"changed_files": ["README.md"]}
    proc = _run_gate(tmp_path, "g4", payload)
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["status"] == "skipped"


def test_cli_g1_with_all_fields_passes(tmp_path):
    payload = {
        "changed_files": ["src/x.py", "tests/test_x.py"],
        "approvals": [{"change_id": "c", "tests": ["tests/test_x.py"], "approved_by": "a",
                       "approved_at": "2026-11-01T09:00:00+00:00"}],
        "first_implementation_commit": "2026-11-01T10:00:00+00:00",
    }
    proc = _run_gate(tmp_path, "g1", payload)
    assert proc.returncode == 0
