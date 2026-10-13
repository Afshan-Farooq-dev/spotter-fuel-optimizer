from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Point
from apps.stations.models import GeocodingCache, StationLocation
from apps.stations.providers.geocoding import GeocodingError
from apps.stations.services.geocoding import choose_match, geocode_station


def response():
    # Synthetic provider response for tests only, never imported into the application database.
    return {"features":[{"geometry":{"type":"Point","coordinates":[-95.36,29.76]},
        "properties":{"country_a":"USA","region_a":"TX","locality":"Houston",
        "name":"Test Stop","layer":"venue","accuracy":"point","confidence":0.98,
        "label":"Test Stop, Houston, TX"}}]}


def provider(payload=None):
    return SimpleNamespace(name="test-provider", endpoint="https://example.test/geocode",
                           search=Mock(return_value=response() if payload is None else payload))


def test_precise_match_cached(station):
    p = provider()
    first = geocode_station(station,p)
    second = geocode_station(station,p)
    assert first["status"] == "verified" and second["cache_hit"]
    p.search.assert_called_once()
    location = StationLocation.objects.get(station=station)
    assert location.point.x == -95.36 and location.point.y == 29.76
    assert location.point.srid == 4326
    assert GeocodingCache.objects.count() == 1


@pytest.mark.parametrize("change", [
    {"country_a":"CAN"}, {"region_a":"NY"}, {"locality":"Dallas"},
    {"layer":"locality"}, {"accuracy":"centroid"}, {"confidence":0.3}, {"name":"Other Stop"}
])
def test_imprecise_or_mismatched_results_stay_null(station,change):
    payload=response(); payload["features"][0]["properties"].update(change)
    result=geocode_station(station,provider(payload))
    assert result["status"]=="no_match"
    assert StationLocation.objects.get(station=station).point is None


@pytest.mark.parametrize("coordinates", [[95.36,29.76],[-95.36,200],["NaN",29.76],[0,0]])
def test_bad_coordinates_rejected(station,coordinates):
    payload=response(); payload["features"][0]["geometry"]["coordinates"]=coordinates
    assert choose_match(station,payload)[0]=="no_match"


def test_multiple_precise_matches_are_ambiguous(station):
    payload=response(); other=deepcopy(payload["features"][0])
    other["geometry"]["coordinates"]=[-95.37,29.77]; payload["features"].append(other)
    assert geocode_station(station,provider(payload))["status"]=="ambiguous"
    assert StationLocation.objects.get(station=station).point is None


def test_transient_errors_not_cached(station):
    p=provider(); p.search.side_effect=GeocodingError("timeout")
    with pytest.raises(GeocodingError): geocode_station(station,p)
    assert GeocodingCache.objects.count()==0
    assert StationLocation.objects.count()==0


def test_model_validates_range(station):
    location=StationLocation(station=station,point=Point(0,100,srid=4326),status="verified",
                             country_code="USA",region_code="TX")
    with pytest.raises(ValidationError): location.full_clean()
