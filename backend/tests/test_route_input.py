import pytest
from apps.routes.api.serializers import OptimizeRouteSerializer

BASE={"start":{"longitude":-95,"latitude":30},"destination":{"longitude":-94,"latitude":30}}


def test_valid_input_defaults():
    s=OptimizeRouteSerializer(data=BASE);assert s.is_valid(),s.errors
    assert s.validated_data["initial_fuel_gallons"]==50


@pytest.mark.parametrize("change",[
    {"start":""},{"start":{"longitude":float("nan"),"latitude":30}},
    {"start":{"longitude":-95,"latitude":100}},{"initial_fuel_gallons":51},
    {"reserve_gallons":50},{"reserve_gallons":10,"initial_fuel_gallons":5},
    {"corridor_metres":5001},{"max_range":600},{"destination":BASE["start"]}
])
def test_invalid_requests_fail_without_provider_calls(change):
    assert not OptimizeRouteSerializer(data={**BASE,**change}).is_valid()
