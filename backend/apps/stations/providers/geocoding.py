"""Replaceable ORS/Pelias adapter; credentials stay in request headers."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GeocodingError(Exception):
    pass


class OpenRouteServiceGeocoder:
    name = "openrouteservice-pelias-v1"
    endpoint = "https://api.openrouteservice.org/geocode/search"

    def __init__(self, api_key, *, timeout=10, retries=2, interval=1):
        self.api_key, self.timeout, self.retries = api_key, timeout, retries
        self.interval, self.last_call = interval, 0.0

    def search(self, query):
        if not self.api_key:
            raise GeocodingError("Set ORS_API_KEY in your local .env before making geocoding calls.")
        params = {"text": ", ".join([query["name"], query["address"], query["city"], query["state"], "USA"]),
                  "boundary.country": "USA", "size": 5}
        request = Request(self.endpoint + "?" + urlencode(params),
                          headers={"Authorization": self.api_key, "User-Agent": "SpotterFuelOptimizer/1.0"})
        for attempt in range(self.retries + 1):
            time.sleep(max(0, self.interval - (time.monotonic() - self.last_call)))
            self.last_call = time.monotonic()
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = response.read(2_000_001)
                if len(payload) > 2_000_000:
                    raise GeocodingError("Geocoding response exceeded the size limit.")
                result = json.loads(payload)
                if not isinstance(result, dict) or not isinstance(result.get("features"), list):
                    raise GeocodingError("Geocoding provider returned an invalid response.")
                return result
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise GeocodingError(f"Geocoding provider returned HTTP {exc.code}.") from None
            except (URLError, TimeoutError, OSError):
                if attempt == self.retries:
                    raise GeocodingError("Geocoding provider was unreachable or timed out.") from None
            except (ValueError, UnicodeError):
                raise GeocodingError("Geocoding provider returned invalid JSON.") from None
            time.sleep(2 ** attempt)
