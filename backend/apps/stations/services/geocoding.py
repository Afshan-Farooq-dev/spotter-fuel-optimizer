"""Persist raw provider responses; accept only precise, unambiguous US matches."""
import hashlib
import json
import math
import re
from datetime import timedelta
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone
from ..models import FuelStation, GeocodingCache, StationLocation
from ..providers.geocoding import GeocodingError
from apps.routes.services.locations import us_state
from apps.routes.services.domain import InvalidLocation,ProviderError


def normalized(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def station_query(station):
    return {key: getattr(station, key) for key in ("name", "address", "city", "state")}


def choose_match(station, response, *, min_confidence=0.9):
    if not isinstance(response, dict) or not isinstance(response.get("features"), list):
        raise GeocodingError("Invalid cached provider response.")
    accepted = {}
    for feature in response["features"]:
        try:
            properties = feature["properties"]
            geometry = feature["geometry"]
            coordinates = geometry["coordinates"]
            if geometry["type"] != "Point" or len(coordinates) != 2:
                continue
            lon, lat = map(float, coordinates)
            confidence = float(properties.get("confidence", 0))
            if not all(math.isfinite(v) for v in (lon, lat, confidence)):
                continue
            if not (-180 <= lon <= 180 and -90 <= lat <= 90 and min_confidence <= confidence <= 1):
                continue
            if properties.get("country_a") != "USA" or properties.get("region_a") != station.state:
                continue
            # Plausibility checks complement country/state metadata; these are not boundary polygons.
            if station.state == "AK":
                plausible = (lon <= -129 or lon >= 170) and 50 <= lat <= 72
            elif station.state == "HI":
                plausible = -161 <= lon <= -154 and 18 <= lat <= 23
            else:
                plausible = -125 <= lon <= -66 and 24 <= lat <= 50
            if not plausible:
                continue
            cities = [properties.get("locality", ""), properties.get("localadmin", "")]
            if normalized(station.city) not in {normalized(city) for city in cities}:
                continue
            layer = properties.get("layer")
            if properties.get("accuracy") != "point" or layer not in ("venue", "address"):
                continue
            if layer == "venue":
                if normalized(properties.get("name", "")) not in {normalized(s) for s in station.aliases + [station.name]}:
                    continue
            else:
                matched = " ".join([str(properties.get("housenumber", "")), str(properties.get("street", ""))])
                if normalized(matched) != normalized(station.address):
                    continue
            accepted[(lon, lat)] = {
                "point": Point(lon, lat, srid=4326), "confidence": confidence,
                "precision": layer, "matched_address": properties.get("label", ""),
                "country_code": "USA", "region_code": station.state,
            }
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    if len(accepted) == 1:
        return StationLocation.Status.VERIFIED, next(iter(accepted.values()))
    return (StationLocation.Status.AMBIGUOUS if accepted else StationLocation.Status.NO_MATCH), {}


def geocode_station(station, provider, *, refresh=False, cache_days=30, min_confidence=0.9):
    # Refreshing one provider must not discard another provider's verified evidence.
    if StationLocation.objects.filter(station=station, status="verified").exclude(provider=provider.name).exists():
        return {"station_id": station.pk, "status": "verified", "cache_hit": True, "preserved_existing": True}
    query = station_query(station)
    cache_identity = {"provider": provider.name, "endpoint": provider.endpoint,
                      "query": {k: normalized(v) for k, v in query.items()}}
    key = hashlib.sha256(json.dumps(cache_identity, sort_keys=True).encode()).hexdigest()
    cache = GeocodingCache.objects.filter(key=key,
        fetched_at__gte=timezone.now() - timedelta(days=cache_days)).first()
    hit = cache is not None and not refresh
    if not hit:
        response = provider.search(query)
        # Reject malformed responses before caching, but cache valid empty/ambiguous results.
        if not isinstance(response, dict) or not isinstance(response.get("features"), list):
            raise GeocodingError("Provider returned an invalid response.")
        cache, _ = GeocodingCache.objects.update_or_create(key=key,
            defaults={"provider": provider.name, "query": query, "response": response, "fetched_at": timezone.now()})
    status, match = choose_match(station, cache.response, min_confidence=min_confidence)
    if status == StationLocation.Status.VERIFIED:
        try:
            if us_state(match["point"].x,match["point"].y) != station.state:
                status,match = StationLocation.Status.NO_MATCH,{}
        except InvalidLocation:
            status,match = StationLocation.Status.NO_MATCH,{}
        except ProviderError as error:
            raise GeocodingError(str(error)) from None
    with transaction.atomic():
        locked = FuelStation.objects.select_for_update().get(pk=station.pk)
        if station_query(locked) != query:
            raise GeocodingError("Station address changed during geocoding; retry.")
        location, _ = StationLocation.objects.get_or_create(station=locked)
        if location.status == "verified" and location.provider != provider.name:
            return {"station_id": station.pk, "status": "verified", "cache_hit": True, "preserved_existing": True}
        location.point = match.get("point")
        location.status = status
        location.provider = provider.name
        location.matched_address = match.get("matched_address", "")
        location.country_code = match.get("country_code", "")
        location.region_code = match.get("region_code", "")
        location.confidence = match.get("confidence")
        location.precision = match.get("precision", "")
        location.cache = cache
        location.checked_at = timezone.now()
        location.full_clean()
        location.save()
    return {"station_id": station.pk, "status": status, "cache_hit": hit}

