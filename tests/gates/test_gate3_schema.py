import copy

import check_schema as g3

VALID = {
    "requirements": [
        {
            "id": "REQ-FR-001",
            "type": "functional",
            "priority": "must",
            "statement": "Provide three run profiles.",
            "fit_criterion": [
                {"metric": "matrix", "threshold": "== 1.0", "verification": "pytest x"},
            ],
        },
        {
            "id": "REQ-INV-003",
            "type": "invariant",
            "priority": "must",
            "statement": "Rating authority is deterministic.",
            "fit_criterion": [
                {"metric": "escapes", "threshold": "== 0", "verification": "pytest y"},
            ],
        },
    ]
}


def test_valid_registry_passes():
    result = g3.check(VALID)
    assert result.passed


def test_missing_fit_criterion_field_fails():
    bad = copy.deepcopy(VALID)
    del bad["requirements"][0]["fit_criterion"][0]["threshold"]
    result = g3.check(bad)
    assert not result.passed
    assert any("fit-criterion" in v.reason for v in result.violations)


def test_empty_fit_criterion_list_fails():
    bad = copy.deepcopy(VALID)
    bad["requirements"][0]["fit_criterion"] = []
    result = g3.check(bad)
    assert not result.passed


def test_priority_out_of_moscow_fails():
    bad = copy.deepcopy(VALID)
    bad["requirements"][0]["priority"] = "High"
    result = g3.check(bad)
    assert not result.passed
    assert any("MoSCoW" in v.reason for v in result.violations)


def test_duplicate_id_fails():
    bad = copy.deepcopy(VALID)
    bad["requirements"][1]["id"] = "REQ-FR-001"
    bad["requirements"][1]["type"] = "functional"  # keep type consistent, only duplication trips
    result = g3.check(bad)
    assert not result.passed
    assert any("duplicate id" in v.reason for v in result.violations)


def test_id_type_mismatch_fails():
    bad = copy.deepcopy(VALID)
    bad["requirements"][0]["type"] = "security"  # needs REQ-SEC prefix, id is REQ-FR
    result = g3.check(bad)
    assert not result.passed
    assert any("mismatch" in v.reason for v in result.violations)


def test_bare_list_registry_accepted():
    result = g3.check(VALID["requirements"])
    assert result.passed
