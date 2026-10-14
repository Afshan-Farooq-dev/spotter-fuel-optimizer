"""Cached, bounded Overpass downloads for offline station enrichment."""
import hashlib
import json
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from django.utils import timezone
from ..models import GeocodingCache

class OSMError(Exception):
    pass

def cache_file(path):
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload.get('elements'), list) or payload.get('remark'):
        raise OSMError('Expected a complete OSM JSON extract.')
    key = hashlib.sha256(raw).hexdigest()
    return GeocodingCache.objects.get_or_create(key=key, defaults={
        'provider':'osm-file-v1', 'query':{'file':path.name,'sha256':key}, 'response':payload})[0]

def extract(bbox, endpoint='https://overpass-api.de/api/interpreter', refresh=False):
    south,west,north,east=bbox
    if not (-90<=south<north<=90 and -180<=west<east<=180):
        raise OSMError('Invalid south,west,north,east bounds.')
    if (north-south)*(east-west)>6:
        raise OSMError('Use regional extracts for areas exceeding six square degrees.')
    query=f'[out:json][timeout:25][maxsize:33554432];nwr[amenity=fuel]({south},{west},{north},{east});out geom;'
    key=hashlib.sha256((endpoint+query).encode()).hexdigest()
    cached=GeocodingCache.objects.filter(key=key).first()
    now=timezone.now()
    if cached and cached.response.get('retry_at',0)>now.timestamp():
        raise OSMError('Provider cooldown active; resume after cached retry_at.')
    if cached and not refresh and cached.fetched_at>now-timedelta(days=30):
        return cached,True
    request=Request(endpoint,data=urlencode({'data':query}).encode(),headers={
        'User-Agent':'SpotterFuelOptimizer/2.0 (offline station enrichment)',
        'Content-Type':'application/x-www-form-urlencoded'})
    try:
        with urlopen(request,timeout=40) as response:
            raw=response.read(16*1024*1024+1)
        if len(raw)>16*1024*1024:raise OSMError('Response exceeded 16 MiB.')
        payload=json.loads(raw)
        if not isinstance(payload.get('elements'),list) or payload.get('remark'):
            raise OSMError('Incomplete response; nothing imported.')
    except HTTPError as error:
        if error.code in (429,502,503,504):
            try:delay=max(60,min(86400,int(error.headers.get('Retry-After',300))))
            except ValueError:delay=300
            GeocodingCache.objects.update_or_create(key=key,defaults={'provider':'osm-overpass-v1',
                'query':{'endpoint':endpoint,'query':query},'response':{'retry_at':now.timestamp()+delay},'fetched_at':now})
        raise OSMError(f'Overpass HTTP {error.code}; stopped without automatic retries.') from None
    except (URLError,TimeoutError,ValueError) as error:
        raise OSMError(f'Overpass unavailable: {type(error).__name__}') from None
    cached,_=GeocodingCache.objects.update_or_create(key=key,defaults={'provider':'osm-overpass-v1',
        'query':{'endpoint':endpoint,'query':query},'response':payload,'fetched_at':now})
    return cached,False
