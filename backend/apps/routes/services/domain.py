"""Pure route/fuel domain types and exact unit conversions."""
from dataclasses import dataclass
from decimal import Decimal

METRES_PER_MILE = Decimal("1609.344")
MAX_RANGE_MILES = Decimal("500")
MPG = Decimal("10")
TANK_GALLONS = MAX_RANGE_MILES / MPG


class PlanningError(Exception):
    code = "infeasible_route"
    status = 422


class ProviderError(PlanningError):
    code = "routing_provider_unavailable"
    status = 503


class InvalidLocation(PlanningError):
    code = "invalid_location"
    status = 400


@dataclass(frozen=True)
class Candidate:
    station_id: int
    miles: Decimal
    price: Decimal
    longitude: float | None = None
    latitude: float | None = None


@dataclass(frozen=True)
class Purchase:
    station_id: int
    miles: Decimal
    price: Decimal
    gallons: Decimal
    arrival_gallons: Decimal
    departure_gallons: Decimal

    @property
    def cost(self):
        return self.price * self.gallons


@dataclass(frozen=True)
class FuelPlan:
    purchases: tuple[Purchase, ...]
    distance_miles: Decimal
    initial_gallons: Decimal
    remaining_gallons: Decimal

    @property
    def consumed_gallons(self):
        return self.distance_miles / MPG

    @property
    def purchased_gallons(self):
        return sum((p.gallons for p in self.purchases), Decimal(0))

    @property
    def total_cost(self):
        return sum((p.cost for p in self.purchases), Decimal(0))


def miles_from_metres(value):
    return Decimal(str(value)) / METRES_PER_MILE
