"""Resolve textual endpoints once and validate coordinates against Census polygons."""
import hashlib,json,math
from datetime import timedelta
from urllib.parse import urlencode
from django.contrib.gis.geos import Point
from django.utils import timezone
from apps.stations.models import GeocodingCache
from ..models import USStateBoundary
from .domain import InvalidLocation,ProviderError


def us_state(longitude,latitude):
    if not all(math.isfinite(float(v)) for v in (longitude,latitude)):
        raise InvalidLocation("Coordinates must be finite.")
    if not (-180<=longitude<=180 and -90<=latitude<=90):raise InvalidLocation("Invalid longitude or latitude.")
    if not USStateBoundary.objects.exists():raise ProviderError("Import US Census boundaries before planning routes.")
    state=USStateBoundary.objects.filter(geometry__covers=Point(longitude,latitude,srid=4326)).values_list("code",flat=True).first()
    if state is None:raise InvalidLocation("Start and destination must lie within the 50 US states or DC.")
    return state


class EndpointResolver:
    endpoint="https://api.openrouteservice.org/geocode/search"
    name="ors-endpoints-v1"

    def __init__(self,client):
        self.client=client;self.geocoding_calls=0;self.cache_hits=0

    def resolve(self,value):
        if isinstance(value,dict):
            lon,lat=float(value["longitude"]),float(value["latitude"])
            return {"longitude":lon,"latitude":lat,"state":us_state(lon,lat),"label":None}
        text=" ".join(value.strip().split())
        identity={"provider":self.name,"country":"USA","text":text.casefold()}
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        cached=GeocodingCache.objects.filter(key=key,fetched_at__gte=timezone.now()-timedelta(days=30)).first()
        if cached:
            self.cache_hits+=1;payload=cached.response
        else:
            params={"text":text,"boundary.country":"USA","size":5}
            before=self.client.calls
            try:payload=self.client.json_request(self.endpoint+"?"+urlencode(params))
            finally:self.geocoding_calls+=self.client.calls-before
            if not isinstance(payload.get("features"),list):raise ProviderError("Invalid endpoint geocoding response.")
            GeocodingCache.objects.update_or_create(key=key,defaults={"provider":self.name,"query":identity,
                "response":payload,"fetched_at":timezone.now()})
        matches={}
        for feature in payload.get("features",[]):
            try:
                props=feature["properties"];geom=feature["geometry"]
                lon,lat=map(float,geom["coordinates"]);confidence=float(props.get("confidence",0))
                if geom["type"]!="Point" or props.get("country_a")!="USA" or not 0.75<=confidence<=1:continue
                state=us_state(lon,lat)
                matches[(lon,lat)]={"longitude":lon,"latitude":lat,"state":state,
                                   "label":props.get("label",text),"confidence":confidence}
            except (KeyError,TypeError,ValueError,InvalidLocation):continue
        ranked=sorted(matches.values(),key=lambda m:m["confidence"],reverse=True)
        if not ranked or (len(ranked)>1 and ranked[0]["confidence"]-ranked[1]["confidence"]<0.05):
            raise InvalidLocation("No unambiguous US endpoint match; provide longitude and latitude.")
        return {key:value for key,value in ranked[0].items() if key!="confidence"}
