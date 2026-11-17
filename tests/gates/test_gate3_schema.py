import copy

import check_schema as g3

VALID = {
    "entries": [
        {
            "id": "REQ-FR-001",
            "type": "REQ-FR",
            "priority": "Must",
            "statement": "Provide three run profiles.",
            "fit_criterion": {"metric": "matrix", "threshold": "==1.0", "verification": "pytest x"},
        },
        {
            "id": "REQ-INV-003",
            "type": "REQ-INV",
            "priority": "Must",
            "statement": "Rating authority is deterministic.",
            "fit_criterion": {"metric": "escapes", "threshold": "==0", "verification": "pytest y"},
        },
    ]
}


def test_valid_registry_passes():
    result = g3.check(VALID)
    assert result.passed


def test_missing_fit_criterion_field_fails():
    bad = copy.deepcopy(VALID)
    del bad["entries"][0]["fit_criterion"]["threshold"]
    result = g3.check(bad)
    assert not result.passed
    assert any("fit-criterion" in v.reason for v in result.violations)


def test_priority_out_of_moscow_fails():
    bad = copy.deepcopy(VALID)
    bad["entries"][0]["priority"] = "High"
    result = g3.check(bad)
    assert not result.passed
    assert any("MoSCoW" in v.reason for v in result.violations)


def test_duplicate_id_fails():
    bad = copy.deepcopy(VALID)
    bad["entries"][1]["id"] = "REQ-FR-001"
    # keep type consistent with the (now duplicated) id so only duplication trips
    bad["entries"][1]["type"] = "REQ-FR"
    result = g3.check(bad)
    assert not result.passed
    assert any("duplicate id" in v.reason for v in result.violations)


def test_id_type_mismatch_fails():
    bad = copy.deepcopy(VALID)
    bad["entries"][0]["type"] = "REQ-SEC"
    result = g3.check(bad)
    assert not result.passed
    assert any("mismatch" in v.reason for v in result.violations)


def test_bare_list_registry_accepted():
    result = g3.check(VALID["entries"])
    assert result.passed
