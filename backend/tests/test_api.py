from unittest.mock import patch
import pytest
from django.db import OperationalError
from rest_framework.test import APIClient


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_health(api):
    assert api.get("/api/health/").json() == {"status":"ok","database":"ok"}


def test_health_db_failure(api):
    with patch("apps.stations.api.views.connection.cursor", side_effect=OperationalError("private connection data")):
        response=api.get("/api/health/")
    assert response.status_code==503
    assert "private" not in str(response.content)


def test_station_list_detail_and_filters(api,station):
    response=api.get("/api/stations/?state=tx")
    assert response.status_code==200 and response.json()["count"]==1
    item=response.json()["results"][0]
    assert item["median_price"]=="3.1234567800"
    assert item["location"]=={"status":"unresolved","coordinates":None}
    assert api.get(f"/api/stations/{station.pk}/").json()["source_id"]=="123"
    assert api.get("/api/stations/?geocoded=true").json()["count"]==0
    assert api.get("/api/stations/?geocoded=false").json()["count"]==1
    assert api.get("/api/stations/?state=ON").status_code==400
    assert api.get("/api/stations/?geocoded=maybe").status_code==400
    assert api.get("/api/stations/999999/").status_code==404
    assert api.post("/api/stations/",{}).status_code==405


def test_pagination_and_no_per_station_queries(api,station,django_assert_num_queries):
    from apps.stations.models import FuelStation
    FuelStation.objects.bulk_create([FuelStation(source_id=str(i),name=f"Stop {i}",aliases=[],
        address="Road",city="Town",state="TX",median_price="3",active_dataset=station.active_dataset)
        for i in range(200,230)])
    with django_assert_num_queries(2):
        response=api.get("/api/stations/?page_size=10")
        assert len(response.json()["results"])==10
        assert response.json()["next"]
    assert api.get("/api/stations/?page_size=1000").json()["count"]==31
    assert api.get("/api/stations/?search=Test").json()["count"]==1
