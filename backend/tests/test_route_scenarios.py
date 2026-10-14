from decimal import Decimal as D
from unittest.mock import patch
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from apps.routes.services.domain import Candidate
from apps.stations.models import FuelStation
from test_planning import FixedResolver,SyntheticDirections,DATA
from test_locations import texas_boundary


def test_multiple_stops_conserve_fuel_and_cost(station):
    cache.clear()
    second=FuelStation.objects.create(source_id="200",name="Second test stop",aliases=[],address="Road",
        city="Town",state="TX",median_price="2",active_dataset=station.active_dataset)
    third=FuelStation.objects.create(source_id="201",name="Third test stop",aliases=[],address="Road",
        city="Town",state="TX",median_price="4",active_dataset=station.active_dataset)
    stations=[station,second,third];positions=[400,800,1200];longitudes=[-94.75,-94.5,-94.25]
    candidates=[Candidate(s.pk,D(position),D(s.median_price),longitude,30)
                for s,position,longitude in zip(stations,positions,longitudes)]
    provider=SyntheticDirections(1500,dict(zip(longitudes,positions)))
    with patch("apps.routes.services.planning.ORSDirections",return_value=provider), \
         patch("apps.routes.services.planning.EndpointResolver",return_value=FixedResolver()), \
         patch("apps.routes.services.planning.route_candidates",return_value=candidates):
        response=APIClient().post("/api/routes/optimize/",DATA,format="json")
    assert response.status_code==200,response.json()
    result=response.json();assert len(result["fuel_stops"])==3
    assert sum(D(s["cost"]) for s in result["fuel_stops"])==D(result["total_cost"])
    assert abs(D(result["initial_fuel_gallons"])+D(result["fuel_purchased_gallons"])
               -D(result["fuel_consumed_gallons"])-D(result["remaining_fuel_gallons"]))<D("0.000000001")
    assert all(D(s["departure_fuel_gallons"])<=50 for s in result["fuel_stops"])
    assert result["provider_usage"]["directions_calls"]==2


@pytest.mark.django_db
def test_long_trip_without_verified_station_coverage_returns_422():
    cache.clear();provider=SyntheticDirections(900)
    with patch("apps.routes.services.planning.ORSDirections",return_value=provider), \
         patch("apps.routes.services.planning.EndpointResolver",return_value=FixedResolver()), \
         patch("apps.routes.services.planning.route_candidates",return_value=[]):
        response=APIClient().post("/api/routes/optimize/",DATA,format="json")
    assert response.status_code==422
    assert response.json()["error"]["code"]=="insufficient_station_coverage"
    assert "fuel_constraints_verified" not in response.json()["error"]["details"]


def test_non_us_endpoint_is_rejected_before_routing(texas_boundary):
    cache.clear()
    data={**DATA,"start":{"longitude":-79.38,"latitude":43.65}}
    with patch("apps.routes.providers.directions.ORSDirections.fetch") as provider:
        response=APIClient().post("/api/routes/optimize/",data,format="json")
    assert response.status_code==400
    provider.assert_not_called()
