"""Cache provider geometry independently of station prices and fuel plans."""
import hashlib,json
from datetime import timedelta
from django.utils import timezone
from ..models import RouteGeometryCache
from ..providers.directions import parse_directions


def driving_route(provider,coordinates,*,ttl_seconds=86400):
    identity={"provider":provider.name,"endpoint":provider.endpoint,"coordinates":coordinates,
              "profile":"driving-car","avoid_borders":"all","geometry_simplify":False,
              "instructions":len(coordinates)>2}
    key=hashlib.sha256(json.dumps(identity,sort_keys=True,allow_nan=False).encode()).hexdigest()
    cached=RouteGeometryCache.objects.filter(key=key,expires_at__gt=timezone.now()).first()
    if cached is not None:
        provider.cache_hits+=1
        return parse_directions(cached.payload,len(coordinates))
    payload=provider.fetch(coordinates)
    route=parse_directions(payload,len(coordinates))
    RouteGeometryCache.objects.update_or_create(key=key,defaults={"provider":provider.name,
        "coordinates":coordinates,"payload":payload,"expires_at":timezone.now()+timedelta(seconds=ttl_seconds)})
    return route
