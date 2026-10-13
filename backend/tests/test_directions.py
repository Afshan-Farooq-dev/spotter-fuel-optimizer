from copy import deepcopy
from decimal import Decimal
import pytest
from apps.routes.providers.directions import parse_directions
from apps.routes.services.domain import ProviderError


def route_payload(distance=1609.344):
    return {"features":[{"geometry":{"type":"LineString","coordinates":[[-95,30],[-94.99,30]]},
        "properties":{"summary":{"distance":distance,"duration":60},
            "segments":[{"distance":distance}],"way_points":[0,1]}}]}


def test_parse_geometry_and_miles():
    parsed=parse_directions(route_payload(),2)
    assert parsed.miles==1 and parsed.leg_metres==(Decimal("1609.344"),)


@pytest.mark.parametrize("kind",["point","nan","legs","waypoints"])
def test_invalid_route_metadata(kind):
    payload=route_payload();feature=payload["features"][0]
    if kind=="point":feature["geometry"]["type"]="Point"
    elif kind=="nan":feature["geometry"]["coordinates"][0][0]=float("nan")
    elif kind=="legs":feature["properties"]["segments"][0]["distance"]=1
    else:feature["properties"]["way_points"]=[1,0]
    with pytest.raises(ProviderError):parse_directions(payload,2)
