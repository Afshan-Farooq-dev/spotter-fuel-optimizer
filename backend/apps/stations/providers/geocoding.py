"""Genuine ORS station matches, spatially focused around cached source localities."""
import hashlib,json
from datetime import timedelta
from urllib.parse import urlencode
from django.utils import timezone
from apps.stations.models import GeocodingCache
from apps.routes.providers.http import ORSClient
from apps.routes.services.domain import ProviderError


class GeocodingError(Exception):
    pass


def normalize(value):return " ".join(str(value).casefold().split())


class OpenRouteServiceGeocoder:
    name="openrouteservice-pelias-v3"
    endpoint="https://api.openrouteservice.org/geocode/search"

    def __init__(self,api_key,*,timeout=10,retries=2,interval=1.6):
        self.client=ORSClient(api_key,timeout=timeout,retries=retries,interval=interval)

    def fetch(self,params):
        try:payload=self.client.json_request(self.endpoint+"?"+urlencode(params))
        except ProviderError as error:raise GeocodingError(str(error)) from None
        if not isinstance(payload.get("features"),list):raise GeocodingError("Invalid geocoding response.")
        return payload

    def locality_focus(self,query):
        identity={"city":normalize(query["city"]),"state":query["state"],"country":"USA"}
        key=hashlib.sha256(("ors-station-locality-v1:"+json.dumps(identity,sort_keys=True)).encode()).hexdigest()
        cached=GeocodingCache.objects.filter(key=key,fetched_at__gte=timezone.now()-timedelta(days=30)).first()
        if cached:payload=cached.response
        else:
            payload=self.fetch({"text":query["city"]+", "+query["state"]+", USA","boundary.country":"USA",
                                "layers":"locality,localadmin","size":5})
            GeocodingCache.objects.update_or_create(key=key,defaults={"provider":"ors-station-locality-v1",
                "query":identity,"response":payload,"fetched_at":timezone.now()})
        accepted=set()
        for feature in payload["features"]:
            try:
                props=feature["properties"];point=feature["geometry"]
                if (props.get("country_a")=="USA" and props.get("region_a")==query["state"]
                    and normalize(props.get("name",""))==normalize(query["city"])
                    and float(props.get("confidence",0))>=0.8 and point["type"]=="Point"):
                    accepted.add(tuple(point["coordinates"]))
            except (KeyError,TypeError,ValueError):continue
        return next(iter(accepted)) if len(accepted)==1 else None

    def search(self,query):
        # The locality point is only a search boundary, never a station-coordinate fallback.
        focus=self.locality_focus(query)
        full=", ".join([query["name"],query["address"],query["city"],query["state"],"USA"])
        features=[]
        for text,layers in [(full,None),(query["name"] if focus else query["name"]+", "+query["city"]+", "+query["state"],"venue")]:
            params={"text":text,"boundary.country":"USA","size":5}
            if layers:params["layers"]=layers
            if focus:
                params.update({"boundary.circle.lon":focus[0],"boundary.circle.lat":focus[1],
                               "boundary.circle.radius":20,"focus.point.lon":focus[0],"focus.point.lat":focus[1]})
            features.extend(self.fetch(params)["features"])
        return {"features":features,"strategy":"source-city-bounded-venue-and-address"}
