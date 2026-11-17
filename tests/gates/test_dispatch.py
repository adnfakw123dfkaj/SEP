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
