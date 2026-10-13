import pytest
from apps.stations.models import FuelDataset, FuelStation


@pytest.fixture
def station(db):
    from django.contrib.gis.geos import MultiPolygon,Polygon
    from apps.routes.models import USStateBoundary
    USStateBoundary.objects.get_or_create(code="TX",defaults={
        "geometry":MultiPolygon(Polygon.from_bbox((-106,25,-93,36)),srid=4326),
        "source_url":"https://example.test/test-only-boundary","source_checksum":"b"*64})
    dataset = FuelDataset.objects.create(checksum="a" * 64, source_name="test.csv", completed=True)
    return FuelStation.objects.create(source_id="123", name="Test Stop", aliases=["Test Stop"],
        address="1 Main Street", city="Houston", state="TX", median_price="3.12345678", active_dataset=dataset)
