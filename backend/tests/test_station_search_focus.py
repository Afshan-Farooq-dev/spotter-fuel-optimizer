from unittest.mock import Mock
from urllib.parse import parse_qs,urlparse
import pytest
from apps.stations.providers.geocoding import OpenRouteServiceGeocoder


@pytest.mark.django_db
def test_city_point_is_only_used_to_focus_search_not_as_station_coordinates():
    city={"features":[{"geometry":{"type":"Point","coordinates":[-95.36,29.76]},
          "properties":{"name":"Houston","region_a":"TX","country_a":"USA","confidence":1}}]}
    provider=OpenRouteServiceGeocoder("test-key")
    provider.client.json_request=Mock(side_effect=[city,{"features":[]},{"features":[]}])
    response=provider.search({"name":"Test Stop","address":"Road","city":"Houston","state":"TX"})
    assert response["features"]==[]
    queries=[parse_qs(urlparse(call.args[0]).query) for call in provider.client.json_request.call_args_list]
    assert queries[-1]["boundary.circle.lon"]==["-95.36"]
    assert queries[-1]["boundary.circle.radius"]==["20"]
