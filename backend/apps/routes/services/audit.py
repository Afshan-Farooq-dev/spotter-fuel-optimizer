"""Audit returned fuel plans independently of the optimization decisions."""
from decimal import Decimal
from .domain import MPG,TANK_GALLONS,PlanningError

TOLERANCE=Decimal("0.000000001")


def audit_fuel_plan(plan,reserve=Decimal(0)):
    fuel=plan.initial_gallons;position=Decimal(0)
    for purchase in plan.purchases:
        if purchase.miles<position or purchase.miles>plan.distance_miles:
            raise PlanningError("Fuel stops are not in route order.")
        fuel-=(purchase.miles-position)/MPG
        if fuel+TOLERANCE<reserve or abs(fuel-purchase.arrival_gallons)>TOLERANCE:
            raise PlanningError("Fuel arrival accounting failed.")
        if purchase.gallons<=0 or purchase.price<=0:
            raise PlanningError("Invalid fuel purchase.")
        fuel+=purchase.gallons
        if fuel>TANK_GALLONS+TOLERANCE or abs(fuel-purchase.departure_gallons)>TOLERANCE:
            raise PlanningError("Tank capacity or departure accounting failed.")
        position=purchase.miles
    fuel-=(plan.distance_miles-position)/MPG
    if fuel+TOLERANCE<reserve or abs(fuel-plan.remaining_gallons)>TOLERANCE:
        raise PlanningError("Destination fuel accounting failed.")
    return True
