"""Validate ORS geometry and waypoint leg distances before using them."""
import math
from dataclasses import dataclass
from decimal import Decimal
from .http import ORSClient
from ..services.domain import ProviderError,miles_from_metres


@dataclass(frozen=True)
class DrivingRoute:
    geometry: dict
    distance_metres: Decimal
    duration_seconds: Decimal
    leg_metres: tuple
    waypoint_indices: tuple

    @property
    def miles(self):return miles_from_metres(self.distance_metres)


def parse_directions(payload,waypoint_count):
    try:
        feature=payload["features"][0];geometry=feature["geometry"];properties=feature["properties"]
        coordinates=geometry["coordinates"]
        if geometry["type"]!="LineString" or len(coordinates)<2:raise ValueError()
        for point in coordinates:
            if len(point)!=2 or not all(math.isfinite(float(v)) for v in point):raise ValueError()
            if not (-180<=float(point[0])<=180 and -90<=float(point[1])<=90):raise ValueError()
        summary=properties["summary"]
        distance=Decimal(str(summary["distance"]));duration=Decimal(str(summary["duration"]))
        segments=properties.get("segments")
        if segments is None and waypoint_count==2:
            legs=(distance,)
        else:
            legs=tuple(Decimal(str(s["distance"])) for s in segments)
        indices=tuple(properties["way_points"])
        if not distance.is_finite() or distance<=0 or not duration.is_finite() or duration<0:raise ValueError()
        if len(legs)!=waypoint_count-1 or any(not v.is_finite() or v<0 for v in legs):raise ValueError()
        if abs(sum(legs)-distance)>Decimal("0.2")*len(legs):raise ValueError()
        if len(indices)!=waypoint_count or any(type(i) is not int or not 0<=i<len(coordinates) for i in indices):raise ValueError()
        if indices[0]!=0 or indices[-1]!=len(coordinates)-1 or list(indices)!=sorted(indices):raise ValueError()
        return DrivingRoute(geometry,distance,duration,legs,indices)
    except (KeyError,IndexError,TypeError,ValueError,ArithmeticError):
        raise ProviderError("ORS returned invalid route geometry or leg distances.") from None


class ORSDirections:
    endpoint="https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    name="ors-driving-car-v1"

    def __init__(self,client):
        self.client=client;self.routing_calls=0;self.cache_hits=0

    def fetch(self,coordinates):
        if not 2<=len(coordinates)<=50:raise ProviderError("ORS requires between 2 and 50 route waypoints.")
        body={"coordinates":coordinates,"instructions":len(coordinates)>2,"geometry_simplify":False,
              "options":{"avoid_borders":"all"}}
        before=self.client.calls
        try:payload=self.client.json_request(self.endpoint,body=body)
        finally:self.routing_calls+=self.client.calls-before
        parse_directions(payload,len(coordinates))
        return payload
