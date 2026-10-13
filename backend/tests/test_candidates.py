from decimal import Decimal
from django.contrib.gis.geos import Point
from apps.stations.models import StationLocation
from apps.routes.providers.directions import parse_directions
from apps.routes.services.candidates import route_candidates


def test_postgis_corridor_includes_only_verified_nearby_station(station):
    payload={"features":[{"geometry":{"type":"LineString","coordinates":[[-95.5,29.76],[-95,29.76]]},
        "properties":{"summary":{"distance":50000,"duration":2000},"segments":[{"distance":50000}],"way_points":[0,1]}}]}
    route=parse_directions(payload,2)
    location=StationLocation.objects.create(station=station,point=Point(-95.36,29.76,srid=4326),
        status="verified",country_code="USA",region_code="TX",confidence=1)
    found=route_candidates(route,corridor_metres=100)
    assert len(found)==1 and found[0].station_id==station.pk
    assert 0<found[0].miles<route.miles
    location.point=Point(-96,30.5,srid=4326);location.save()
    assert route_candidates(route,corridor_metres=100)==[]
