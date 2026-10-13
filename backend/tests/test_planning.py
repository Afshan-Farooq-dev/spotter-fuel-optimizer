from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from apps.routes.services.planning import plan_route
from apps.routes.services.domain import Candidate,PlanningError


class FixedResolver:
    geocoding_calls=0;cache_hits=0
    def resolve(self,value):return {**value,"state":"TX","label":None}


class SyntheticDirections:
    name="synthetic-tests-only";endpoint="https://example.test/route"
    routing_calls=0;cache_hits=0
    def __init__(self,miles,positions=None,final_extra=0):
        self.miles=miles;self.positions=positions or {};self.final_extra=final_extra
    def fetch(self,coordinates):
        self.routing_calls+=1
        positions=[0]+[self.positions[c[0]] for c in coordinates[1:-1]]+[self.miles]
        legs=[(b-a)*1609.344 for a,b in zip(positions,positions[1:])]
        if len(coordinates)>2:legs[0]+=self.final_extra*1609.344
        return {"features":[{"geometry":{"type":"LineString","coordinates":coordinates},
            "properties":{"summary":{"distance":sum(legs),"duration":500},"segments":[{"distance":s} for s in legs],
                          "way_points":list(range(len(coordinates)))}}]}


DATA={"start":{"longitude":-95,"latitude":30},"destination":{"longitude":-94,"latitude":30}}


@pytest.mark.django_db
def test_short_route_uses_one_call_and_cached_repeat():
    provider=SyntheticDirections(200)
    result=plan_route(DATA,provider=provider,resolver=FixedResolver())
    assert result["total_cost"]=="0.00" and result["fuel_stops"]==[]
    assert provider.routing_calls==1
    plan_route(DATA,provider=provider,resolver=FixedResolver())
    assert provider.routing_calls==1 and provider.cache_hits==1


def test_long_route_verifies_actual_stop_distances(station):
    provider=SyntheticDirections(800,{-94.5:400})
    candidate=Candidate(station.pk,Decimal(400),Decimal(3),-94.5,30)
    with patch("apps.routes.services.planning.route_candidates",return_value=[candidate]):
        result=plan_route(DATA,provider=provider,resolver=FixedResolver())
    assert provider.routing_calls==2 and len(result["fuel_stops"])==1
    assert result["fuel_purchased_gallons"]=="30"
    assert result["total_cost"]=="90.00"


def test_driving_detour_cannot_break_maximum_range(station):
    provider=SyntheticDirections(800,{-94.5:400},final_extra=110)
    candidate=Candidate(station.pk,Decimal(400),Decimal(3),-94.5,30)
    with patch("apps.routes.services.planning.route_candidates",return_value=[candidate]):
        with pytest.raises(PlanningError) as error:plan_route(DATA,provider=provider,resolver=FixedResolver())
    assert error.value.code=="verified_route_infeasible"
