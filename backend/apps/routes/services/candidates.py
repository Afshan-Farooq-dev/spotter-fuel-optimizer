"""One spatial query finds verified US stations and estimated baseline chainage."""
from decimal import Decimal
from django.contrib.gis.geos import LineString
from django.db.models import BooleanField,FloatField
from django.db.models.expressions import RawSQL
from apps.stations.models import StationLocation
from .domain import Candidate,PlanningError


def route_candidates(route,*,corridor_metres=2000,limit=10000):
    line=LineString(route.geometry["coordinates"],srid=4326);wkt=line.wkt
    near=RawSQL("ST_DWithin(point::geography,ST_GeomFromText(%s,4326)::geography,%s)",
                [wkt,corridor_metres],output_field=BooleanField())
    fraction=RawSQL("""ST_Length(ST_LineSubstring(ST_GeomFromText(%s,4326),0,
        ST_LineLocatePoint(ST_GeomFromText(%s,4326),point))::geography) /
        NULLIF(ST_Length(ST_GeomFromText(%s,4326)::geography),0)""",
        [wkt,wkt,wkt],output_field=FloatField())
    locations=list(StationLocation.objects.filter(status="verified",country_code="USA",point__isnull=False)
        .select_related("station").annotate(near_route=near,route_fraction=fraction)
        .filter(near_route=True).order_by("route_fraction","station_id")[:limit+1])
    if len(locations)>limit:raise PlanningError("Too many route candidates; narrow the corridor.")
    return [Candidate(location.station_id,route.miles*Decimal(str(location.route_fraction)),
                      location.station.median_price,location.point.x,location.point.y) for location in locations]
