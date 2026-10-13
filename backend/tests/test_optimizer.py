from decimal import Decimal as D
import pytest
from apps.routes.services.domain import Candidate,PlanningError
from apps.routes.services.optimizer import optimize_fuel


def stop(i,miles,price):
    return Candidate(i,D(str(miles)),D(str(price)))


def test_short_full_tank_requires_no_purchase():
    plan=optimize_fuel(D(200),[])
    assert plan.total_cost==0 and plan.remaining_gallons==30


def test_exact_range_and_beyond_range():
    assert optimize_fuel(500,[]).remaining_gallons==0
    with pytest.raises(PlanningError):optimize_fuel("500.001",[])


def test_buy_only_to_cheaper_station():
    plan=optimize_fuel(900,[stop(1,400,4),stop(2,600,3)])
    assert [(p.station_id,p.gallons) for p in plan.purchases]==[(1,D(10)),(2,D(30))]
    assert plan.total_cost==130


def test_multiple_stops_and_conservation():
    plan=optimize_fuel(1600,[stop(1,400,3),stop(2,800,4),stop(3,1200,2)])
    assert len(plan.purchases)==3
    assert plan.initial_gallons+plan.purchased_gallons-plan.consumed_gallons==plan.remaining_gallons
    assert all(p.departure_gallons<=50 and p.arrival_gallons>=0 for p in plan.purchases)


def test_partial_initial_fuel_and_reserve():
    plan=optimize_fuel(600,[stop(1,100,3),stop(2,450,4)],initial_gallons=20,reserve_gallons=5)
    assert plan.remaining_gallons==5
    assert all(p.arrival_gallons>=5 and p.departure_gallons<=50 for p in plan.purchases)


def test_infeasible_gap_is_rejected():
    with pytest.raises(PlanningError):optimize_fuel(1200,[stop(1,400,3),stop(2,1000,2)])


def test_colocated_prices_and_station_at_destination():
    plan=optimize_fuel(600,[stop(1,400,4),stop(2,400,2),stop(3,600,1)])
    assert [(p.station_id,p.gallons) for p in plan.purchases]==[(2,D(10))]


@pytest.mark.parametrize("initial,reserve",[(51,0),(-1,0),(10,11),(50,50)])
def test_invalid_vehicle_inputs(initial,reserve):
    with pytest.raises(PlanningError):optimize_fuel(100,[],initial_gallons=initial,reserve_gallons=reserve)
