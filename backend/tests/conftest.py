import pytest
from apps.stations.models import FuelDataset, FuelStation


@pytest.fixture
def station(db):
    dataset = FuelDataset.objects.create(checksum="a" * 64, source_name="test.csv", completed=True)
    return FuelStation.objects.create(source_id="123", name="Test Stop", aliases=["Test Stop"],
        address="1 Main Street", city="Houston", state="TX", median_price="3.12345678", active_dataset=dataset)
