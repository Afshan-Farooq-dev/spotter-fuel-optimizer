"""Conservative identity matching; coordinates are existing mapped nodes, never centroids."""
import hashlib
import json
import math
import re
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone
from ..models import FuelStation, GeocodingCache, StationLocation
from .geocoding import normalized, station_query
from apps.routes.services.locations import us_state
from apps.routes.services.domain import InvalidLocation

POLICY='osm-identity-v1'

def identity(station, tags):
    names=station.aliases+[station.name]
    city=normalized(tags.get('addr:city',''))==normalized(station.city)
    state=tags.get('addr:state')==station.state
    if not city or not state:return None
    if tags.get('amenity')!='fuel' or tags.get('disused')=='yes' or tags.get('access')=='private':return None
    if tags.get('ref:opis') and tags['ref:opis']!=station.source_id:return None
    exits=re.findall(r'EXIT\s*(\d+[A-Z]?)',station.address.upper())
    mapped_exit=tags.get('ref:exit')
    if mapped_exit and exits and mapped_exit.upper() not in exits:return None
    extras=(['OPIS ID'] if tags.get('ref:opis')==station.source_id else [])
    if mapped_exit and exits:extras.append('highway_exit')
    osm_names={normalized(tags.get(k,'')) for k in ('name','brand','operator','alt_name')}-{''}
    for name in names:
        match=re.fullmatch(r'(.+?)\s*#\s*(\d+)',name.strip())
        if match and normalized(match[1]) in osm_names and tags.get('ref')==match[2]:
            return ['brand','store_number','city','state']+extras
    address=' '.join([tags.get('addr:housenumber',''),tags.get('addr:street','')])
    exact_name=any(normalized(n) in osm_names for n in names)
    exact_address=bool(tags.get('addr:housenumber')) and normalized(address)==normalized(station.address)
    opis=tags.get('ref:opis')==station.source_id
    if exact_name and (exact_address or opis):
        return ['name','address' if exact_address else 'OPIS ID','city','state']
    # Highway exit alone is not identity proof. Never equate OPIS IDs and store numbers.
    return None

def candidate(station, element):
    tags=element.get('tags',{})
    factors=identity(station,tags)
    if not factors:return None
    if element.get('type')=='node':
        coordinate=element
        precision='mapped_fuel_node'
    elif element.get('type')=='way':
        geometry=element.get('geometry',[])
        if len(geometry)<4 or geometry[0]!=geometry[-1]:return None
        coordinate=geometry[0]  # Published OSM vertex on the fuel facility, not computed center.
        precision='mapped_fuel_boundary'
    else:return None
    try:
        lon,lat=float(coordinate['lon']),float(coordinate['lat'])
        if not all(math.isfinite(v) for v in (lon,lat)):return None
        if not (-180<=lon<=180 and -90<=lat<=90):return None
        if us_state(lon,lat)!=station.state:return None
    except (KeyError,TypeError,ValueError,InvalidLocation):return None
    return {'longitude':lon,'latitude':lat,'precision':precision,'factors':factors,
        'osm_url':f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
        'osm_version':element.get('version'),'tags':tags}

def enrich(station, source, refresh=False, dry_run=False):
    query={**station_query(station),'source_id':station.source_id,'aliases':station.aliases}
    key=hashlib.sha256(json.dumps({'policy':POLICY,'station':query,'extract':source.key},sort_keys=True).encode()).hexdigest()
    previous=GeocodingCache.objects.filter(key=key).first()
    if previous and not refresh:return {**previous.response,'resumed':True}
    matches=[m for e in source.response['elements'] if (m:=candidate(station,e))]
    # Multiple objects remain ambiguous even if they are adjacent; no arbitrary branch selection.
    status='verified' if len(matches)==1 else ('ambiguous' if matches else 'no_match')
    evidence={'station_id':station.pk,'status':status,'matches':matches,'policy':POLICY,
        'extract_cache_id':source.pk,'source_station':query,'attribution':'OpenStreetMap contributors',
        'license':'ODbL 1.0','checked_at':timezone.now().isoformat()}
    if dry_run:return evidence
    with transaction.atomic():
        locked=FuelStation.objects.select_for_update().get(pk=station.pk)
        if station_query(locked)!=station_query(station) or locked.aliases!=station.aliases:
            raise ValueError('Station changed; retry enrichment.')
        location,_=StationLocation.objects.get_or_create(station=locked)
        audit,_=GeocodingCache.objects.update_or_create(key=key,defaults={
            'provider':POLICY,'query':query,'response':evidence})
        if location.status=='verified':
            evidence['preserved_existing']=True
            return evidence
        if status=='verified':
            match=matches[0]
            location.point=Point(match['longitude'],match['latitude'],srid=4326)
            location.country_code='USA';location.region_code=station.state
            location.precision=match['precision'];location.confidence=None
            location.matched_address=match['osm_url']
        else:
            location.point=None;location.country_code='';location.region_code=''
            location.precision='';location.confidence=None;location.matched_address=''
        location.status=status;location.provider=POLICY;location.cache=audit
        location.checked_at=timezone.now();location.full_clean();location.save()
    return evidence

