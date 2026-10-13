"""Use ORS/Pelias for genuine station matches, with a conservative venue fallback."""
from urllib.parse import urlencode
from apps.routes.providers.http import ORSClient
from apps.routes.services.domain import ProviderError


class GeocodingError(Exception):
    pass


class OpenRouteServiceGeocoder:
    name="openrouteservice-pelias-v2"
    endpoint="https://api.openrouteservice.org/geocode/search"

    def __init__(self,api_key,*,timeout=10,retries=2,interval=1.6):
        self.client=ORSClient(api_key,timeout=timeout,retries=retries,interval=interval)

    def search(self,query):
        full=", ".join([query["name"],query["address"],query["city"],query["state"],"USA"])
        venue=", ".join([query["name"],query["city"],query["state"],"USA"])
        features=[]
        for text,layers in [(full,None),(venue,"venue")]:
            params={"text":text,"boundary.country":"USA","size":5}
            if layers:params["layers"]=layers
            try:payload=self.client.json_request(self.endpoint+"?"+urlencode(params))
            except ProviderError as error:
                raise GeocodingError(str(error)) from None
            if not isinstance(payload.get("features"),list):raise GeocodingError("Invalid geocoding response.")
            features.extend(payload["features"])
        return {"features":features,"strategy":"source-address-and-source-venue-name"}
