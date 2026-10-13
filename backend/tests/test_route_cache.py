from types import SimpleNamespace
from unittest.mock import Mock
from decimal import Decimal
import pytest
from apps.routes.services.routing import driving_route
from apps.routes.models import RouteGeometryCache
from test_directions import route_payload


@pytest.mark.django_db
def test_cached_geometry_avoids_second_external_request():
    p=SimpleNamespace(name="test",endpoint="https://example.test",cache_hits=0,fetch=Mock(return_value=route_payload()))
    coordinates=[[-95,30],[-94.99,30]]
    first=driving_route(p,coordinates);second=driving_route(p,coordinates)
    assert first==second and p.cache_hits==1
    assert p.fetch.call_count==1 and RouteGeometryCache.objects.count()==1
