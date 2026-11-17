"""TC-P6-BUD-001..006: budget policy behaviour."""

import pytest
from pydantic import ValidationError

from tradingagents.contracts.cost import Budget
from tradingagents.cost.budget import budget_for_profile

pytestmark = pytest.mark.unit


def test_tc_p6_bud_001_profile_hard_limits():
    """TC-P6-BUD-001: the three profiles expose the agreed hard caps."""
    assert budget_for_profile("quick").hard_limit == 25_000
    assert budget_for_profile("standard").hard_limit == 60_000
    assert budget_for_profile("deep").hard_limit == 150_000
    assert budget_for_profile("quick").currency == "CNY"


def test_tc_p6_bud_002_soft_and_hard_boundaries():
    """TC-P6-BUD-002: soft/hard classification uses inclusive boundaries."""
    budget = Budget(profile="test", soft_limit=80, hard_limit=100, currency="CNY")

    assert not budget.is_soft_exceeded(79)
    assert budget.is_soft_exceeded(80)
    assert not budget.is_hard_exceeded(99)
    assert budget.is_hard_exceeded(100)
    assert budget.is_hard_exceeded(101)


def test_tc_p6_bud_003_unknown_profile_rejected():
    """TC-P6-BUD-003: unknown profiles fail loudly, not with a silent default."""
    with pytest.raises(ValueError):
        budget_for_profile("turbo")


def test_tc_p6_bud_004_invalid_budget_rejected():
    """TC-P6-BUD-004: invalid limits never enter routing."""
    with pytest.raises(ValidationError):
        Budget(profile="test", soft_limit=101, hard_limit=100, currency="CNY")

    with pytest.raises(ValidationError):
        Budget(profile="test", soft_limit=-1, hard_limit=100, currency="CNY")

    with pytest.raises(ValidationError):
        Budget(profile="test", soft_limit=0, hard_limit=0, currency="CNY")


def test_tc_p6_bud_005_currency_is_cny():
    """TC-P6-BUD-005: the official DeepSeek page is in CNY, not USD."""
    budget = budget_for_profile("standard")

    assert budget.currency == "CNY"


def test_tc_p6_bud_006_soft_limit_comes_from_profile_config(profile_config):
    """TC-P6-BUD-006: soft limit is read from config, not hard-coded."""
    budget = budget_for_profile("quick", profile_config=profile_config)

    assert budget.soft_limit == profile_config.soft_token_limit
    assert budget.hard_limit == profile_config.hard_token_limit
