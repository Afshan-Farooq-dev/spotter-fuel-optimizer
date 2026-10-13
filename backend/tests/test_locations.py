from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from django.contrib.gis.geos import MultiPolygon,Polygon
from apps.routes.models import USStateBoundary
from apps.routes.services.locations import EndpointResolver
from apps.routes.services.domain import InvalidLocation


@pytest.fixture
def texas_boundary(db):
    # Test boundary only; the application database uses downloaded Census polygons.
    USStateBoundary.objects.create(code="TX",geometry=MultiPolygon(Polygon.from_bbox((-106,25,-93,36)),srid=4326),
                                   source_url="https://example.test/boundary",source_checksum="b"*64)


def test_coordinates_reject_non_us_without_external_calls(texas_boundary):
    client=SimpleNamespace(calls=0,json_request=Mock())
    resolver=EndpointResolver(client)
    assert resolver.resolve({"longitude":-95,"latitude":30})["state"]=="TX"
    with pytest.raises(InvalidLocation):resolver.resolve({"longitude":-79,"latitude":43})
    client.json_request.assert_not_called()


def test_place_text_is_cached(texas_boundary):
    payload={"features":[{"geometry":{"type":"Point","coordinates":[-95,30]},
                          "properties":{"country_a":"USA","confidence":1,"label":"Test Texas location"}}]}
    client=SimpleNamespace(calls=0,json_request=Mock(return_value=payload))
    resolver=EndpointResolver(client)
    assert resolver.resolve("Test Texas location")==resolver.resolve("Test Texas location")
    assert client.json_request.call_count==1
