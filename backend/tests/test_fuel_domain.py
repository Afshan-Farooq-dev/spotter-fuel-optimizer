from decimal import Decimal
from apps.routes.services.domain import MAX_RANGE_MILES,MPG,TANK_GALLONS,miles_from_metres


def test_vehicle_units():
    assert TANK_GALLONS==Decimal(50)
    assert TANK_GALLONS*MPG==MAX_RANGE_MILES
    assert miles_from_metres("1609.344")==1
