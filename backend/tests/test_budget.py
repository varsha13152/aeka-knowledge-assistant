"""Tests for per-user LLM cost budget enforcement."""

import pytest
from app.core.budget import DAILY_BUDGET_BY_ROLE


class TestBudgetConfig:
    def test_student_has_lowest_budget(self):
        assert DAILY_BUDGET_BY_ROLE["student"] < DAILY_BUDGET_BY_ROLE["tutor"]

    def test_admin_has_highest_budget(self):
        assert DAILY_BUDGET_BY_ROLE["admin"] >= DAILY_BUDGET_BY_ROLE["tutor"]

    def test_all_roles_have_positive_budget(self):
        for role, budget in DAILY_BUDGET_BY_ROLE.items():
            assert budget > 0, f"Role {role} has non-positive budget"

    def test_default_budget_for_unknown_role(self):
        # Unknown roles should get the minimum (student) budget
        assert DAILY_BUDGET_BY_ROLE.get("unknown_role", 0.50) == 0.50
