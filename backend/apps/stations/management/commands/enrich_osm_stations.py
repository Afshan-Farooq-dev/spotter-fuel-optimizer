"""Resumable offline enrichment; a single optional Overpass download outside API requests."""
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.stations.models import FuelStation, StationLocation
from apps.stations.providers.osm import cache_file, extract, OSMError
from apps.stations.services.osm_enrichment import enrich

class Command(BaseCommand):
    help='Match an OSM JSON extract conservatively to imported stations.'
    def add_arguments(self,parser):
        source=parser.add_mutually_exclusive_group(required=True)
        source.add_argument('--file',type=Path)
        source.add_argument('--bbox',nargs=4,type=float,metavar=('S','W','N','E'))
        parser.add_argument('--endpoint',default='https://overpass-api.de/api/interpreter')
        parser.add_argument('--state')
        parser.add_argument('--station-id',type=int)
        parser.add_argument('--limit',type=int,default=100)
        parser.add_argument('--refresh',action='store_true')
        parser.add_argument('--dry-run',action='store_true')
    def handle(self,**options):
        if not 1<=options['limit']<=1000:raise CommandError('limit must be 1..1000')
        try:
            cache=cache_file(options['file']) if options['file'] else extract(options['bbox'],options['endpoint'],options['refresh'])[0]
        except (OSMError,OSError,ValueError) as error:raise CommandError(str(error)) from None
        stations=FuelStation.objects.exclude(location__status='verified')
        if options['state']:stations=stations.filter(state=options['state'])
        if options['station_id']:stations=stations.filter(pk=options['station_id'])
        # Each station/extract/policy checkpoint is durable; interrupted runs resume without a provider call.
        processed=0
        for station in stations.iterator(chunk_size=200):
            result=enrich(station,cache,options['refresh'],options['dry_run'])
            if result.get('resumed'):continue
            processed+=1
            self.stdout.write(f"{station.pk}: {result['status']} resumed={result.get('resumed',False)}")
            if processed>=options['limit']:break
        total=FuelStation.objects.count()
        verified=StationLocation.objects.filter(status='verified').count()
        self.stdout.write(f'Verified: {verified}; without verified coordinates: {total-verified}; total: {total}')

