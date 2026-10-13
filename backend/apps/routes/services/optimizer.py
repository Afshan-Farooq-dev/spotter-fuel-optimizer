"""Optimal continuous fuel purchases on a fixed ordered station sequence."""
from decimal import Decimal
from .domain import Candidate,FuelPlan,MPG,PlanningError,Purchase,TANK_GALLONS

EPSILON=Decimal("0.000000000001")


def optimize_fuel(distance_miles, candidates, *, initial_gallons=TANK_GALLONS, reserve_gallons=Decimal(0)):
    distance=Decimal(str(distance_miles)); initial=Decimal(str(initial_gallons)); reserve=Decimal(str(reserve_gallons))
    if not all(v.is_finite() for v in (distance,initial,reserve)):
        raise PlanningError("Fuel inputs must be finite.")
    if distance<0 or not 0<=reserve<TANK_GALLONS or not reserve<=initial<=TANK_GALLONS:
        raise PlanningError("Invalid distance, initial fuel or reserve.")
    stations=sorted(candidates,key=lambda s:(s.miles,s.price,s.station_id))
    if len({s.station_id for s in stations})!=len(stations):
        raise PlanningError("Station IDs must be unique in an ordered sequence.")
    for s in stations:
        if not s.miles.is_finite() or not s.price.is_finite() or not 0<=s.miles<=distance or s.price<=0:
            raise PlanningError("Invalid station distance or price.")
    usable=initial-reserve; capacity=TANK_GALLONS-reserve; position=Decimal(0); purchases=[]
    for index,station in enumerate(stations):
        usable-=(station.miles-position)/MPG
        if usable < -EPSILON:
            raise PlanningError(f"No reachable station before mile {station.miles}.")
        usable=max(usable,Decimal(0)); position=station.miles
        required=min(capacity,(distance-position)/MPG)
        for later in stations[index+1:]:
            needed=(later.miles-position)/MPG
            if needed>capacity:break
            if later.price<station.price:
                required=needed
                break
        quantity=max(Decimal(0),required-usable)
        if quantity>EPSILON:
            purchases.append(Purchase(station.station_id,station.miles,station.price,quantity,
                                      usable+reserve,usable+reserve+quantity))
            usable+=quantity
    usable-=(distance-position)/MPG
    if usable < -EPSILON:
        raise PlanningError("Verified fuel coverage does not reach the destination.")
    return FuelPlan(tuple(purchases),distance,initial,max(usable,Decimal(0))+reserve)
