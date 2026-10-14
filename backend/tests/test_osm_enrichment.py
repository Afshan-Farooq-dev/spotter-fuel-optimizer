import pytest
from apps.stations.services.osm_enrichment import identity, candidate, enrich
from apps.stations.models import GeocodingCache, StationLocation

@pytest.fixture
def osm_station(station):
    station.name='Test Stop #12';station.aliases=[station.name];station.save()
    return station

def element(**updates):
    tags={'amenity':'fuel','name':'Test Stop','ref':'12','addr:city':'Houston','addr:state':'TX'}
    tags.update(updates)
    return {'id':1234,'type':'node','lon':-95.3,'lat':29.7,'tags':tags}

@pytest.mark.django_db
def test_requires_exact_branch_and_city(osm_station):
    assert identity(osm_station,element()['tags'])
    assert identity(osm_station,element(ref='13')['tags']) is None
    assert identity(osm_station,element(**{'addr:city':'Dallas'})['tags']) is None
    assert identity(osm_station,element(amenity='restaurant')['tags']) is None
    assert identity(osm_station,element(disused='yes')['tags']) is None

@pytest.mark.django_db
def test_actual_vertex_not_centroid(osm_station):
    e=element();e.update(type='way',geometry=[{'lon':-95.3,'lat':29.7},{'lon':-95.2,'lat':29.7},{'lon':-95.2,'lat':29.8},{'lon':-95.3,'lat':29.7}])
    result=candidate(osm_station,e)
    assert result['longitude']==-95.3
    assert result['precision']=='mapped_fuel_boundary'
    e['geometry']=e['geometry'][:-1]
    assert candidate(osm_station,e) is None

@pytest.mark.django_db
def test_reject_nonfinite_and_wrong_state(osm_station):
    e=element();e['lon']=float('nan')
    assert candidate(osm_station,e) is None
    e['lon']=-120
    assert candidate(osm_station,e) is None

@pytest.mark.django_db
def test_resume_and_provenance(osm_station):
    source=GeocodingCache.objects.create(key='c'*64,provider='test',query={},response={'elements':[element()]})
    assert enrich(osm_station,source)['status']=='verified'
    location=StationLocation.objects.get(station=osm_station)
    assert location.cache.response['matches'][0]['osm_url'].endswith('/node/1234')
    assert enrich(osm_station,source)['resumed']

@pytest.mark.django_db
def test_ambiguous_and_dry_run(osm_station):
    source=GeocodingCache.objects.create(key='c'*64,provider='test',query={},response={'elements':[element(),element()]})
    assert enrich(osm_station,source,dry_run=True)['status']=='ambiguous'
    assert not StationLocation.objects.filter(station=osm_station).exists()
    enrich(osm_station,source)
    assert StationLocation.objects.get(station=osm_station).point is None
