import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from ...models import FuelStation, StationLocation
from ...providers.geocoding import GeocodingError, OpenRouteServiceGeocoder
from ...services.geocoding import geocode_station
from ...services.fuel_data import US_STATES


class Command(BaseCommand):
    help = "Geocode a bounded batch; successful/empty responses are cached and ambiguous matches stay null."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--state", choices=sorted(US_STATES))
        parser.add_argument("--station-id", type=int)
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--retry-unresolved", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 100:
            raise CommandError("--limit must be between 1 and 100.")
        stations = FuelStation.objects.order_by("pk")
        if options["state"]:
            stations = stations.filter(state=options["state"])
        if options["station_id"] is not None:
            stations = stations.filter(pk=options["station_id"])
            if not stations.exists():
                raise CommandError("Station not found.")
        elif not options["refresh"]:
            if options["retry_unresolved"]:
                stations = stations.exclude(location__status=StationLocation.Status.VERIFIED)
            else:
                stations = stations.filter(location__isnull=True)
        selected = list(stations[:options["limit"]])
        if options["dry_run"]:
            self.stdout.write(json.dumps({"station_ids": [s.pk for s in selected], "external_calls": 0}))
            return
        provider = OpenRouteServiceGeocoder(settings.ORS_API_KEY, timeout=settings.GEOCODING_TIMEOUT,
                                           interval=settings.GEOCODING_INTERVAL)
        for station in selected:
            try:
                result = geocode_station(station, provider, refresh=options["refresh"],
                    cache_days=settings.GEOCODING_CACHE_DAYS, min_confidence=settings.GEOCODING_MIN_CONFIDENCE)
            except GeocodingError as exc:
                # Stop on provider failure rather than spending the quota on repeated failures.
                raise CommandError(str(exc)) from exc
            self.stdout.write(json.dumps(result))
