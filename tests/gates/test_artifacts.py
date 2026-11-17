"""End-to-end checks against the real committed artifacts.

These verify the gates would pass on the repository's actual registry, eval set
and AI-use log, so a broken artifact fails the self-test rather than only CI.
"""

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "gates"))
sys.path.insert(0, str(REPO / "eval"))

import check_schema as g3  # noqa: E402
import check_semantic_eval as g4  # noqa: E402
import harness  # noqa: E402


def test_registry_passes_schema_gate():
    data = yaml.safe_load((REPO / "docs/req/requirements.yaml").read_text(encoding="utf-8"))
    result = g3.check(data)
    assert result.passed, result.render()
    assert len(data["requirements"]) == 14


def test_fixed_set_passes_eval_thresholds():
    metrics = harness.run_fixed_set()
    result = g4.check(["prompts/placeholder.yaml"], metrics)
    assert result.passed, result.render()


def test_ai_use_log_bootstrap_entry_present():
    data = yaml.safe_load((REPO / "docs/ai-use-log.yaml").read_text(encoding="utf-8"))
    entries = data["entries"]
    assert any(e.get("change_id") == "bootstrap" for e in entries)


def test_workflows_are_valid_yaml():
    for name in ("gates.yml", "ci.yml", "branch-check.yml"):
        text = (REPO / ".github/workflows" / name).read_text(encoding="utf-8")
        assert yaml.safe_load(text) is not None
