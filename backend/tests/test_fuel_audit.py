from decimal import Decimal as D
import pytest
from apps.routes.services.domain import Candidate,FuelPlan,PlanningError,Purchase
from apps.routes.services.optimizer import optimize_fuel
from apps.routes.services.audit import audit_fuel_plan


def test_real_solver_plan_passes_independent_audit():
    plan=optimize_fuel(900,[Candidate(1,D(400),D(3)),Candidate(2,D(700),D(2))])
    assert audit_fuel_plan(plan)


def test_incorrect_tank_accounting_cannot_be_returned():
    corrupted=FuelPlan((Purchase(1,D(100),D(3),D(30),D(40),D(70)),),D(200),D(50),D(60))
    with pytest.raises(PlanningError):audit_fuel_plan(corrupted)
