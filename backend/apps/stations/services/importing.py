"""Transactional, bounded-query imports of a cleaned source snapshot."""
import hashlib
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator
from django.db import connection, transaction
from ..models import FuelDataset, FuelPrice, FuelStation, StationLocation
from .fuel_data import clean_fuel_data, read_fuel_csv


def import_fuel_csv(path, *, dry_run=False):
    path = Path(path)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    cleaned = clean_fuel_data(read_fuel_csv(path))
    if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
        raise ValueError("Source changed during processing")
    if not cleaned.stations:
        raise ValueError("No eligible US stations; nothing imported")
    validate_price = DecimalValidator(18, 10)
    for station in cleaned.stations:
        if len(station.station_id) > 64:
            raise ValueError("Station ID exceeds the supported 64 characters")
        validate_price(station.median_price)
    for record in cleaned.records:
        if len(record.rack_id) > 64:
            raise ValueError(f"Rack ID too long on source row {record.source_row}")
        validate_price(record.price)
    summary = {key: cleaned.report[key] for key in (
        "total_source_rows", "cleaned_us_stations", "retained_us_source_rows",
        "excluded_canadian_rows", "invalid_rows", "duplicate_us_rows", "price_conflict_station_count")}
    if dry_run:
        return {"status": "dry_run", "checksum": checksum, **summary}
    with transaction.atomic():
        # Serialize imports, including different snapshots updating the same station IDs.
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ["spotter-fuel-csv-import"])
        dataset, _ = FuelDataset.objects.get_or_create(checksum=checksum,
            defaults={"source_name": path.name, "report": cleaned.report})
        if dataset.completed:
            return {"status": "already_imported", "checksum": checksum, **summary}
        existing = {s.source_id: s for s in FuelStation.objects.filter(
            source_id__in=[s.station_id for s in cleaned.stations])}
        changed_locations = []
        stations = []
        for station in cleaned.stations:
            previous = existing.get(station.station_id)
            if previous and (previous.address.casefold(), previous.city.casefold(), previous.state) != (
                    station.address.casefold(), station.city.casefold(), station.state):
                changed_locations.append(previous.pk)
            stations.append(FuelStation(source_id=station.station_id, name=station.name,
                aliases=list(station.aliases), address=station.address, city=station.city,
                state=station.state, median_price=station.median_price, active_dataset=dataset,
                price_conflict=len(station.distinct_prices) > 1))
        FuelStation.objects.bulk_create(stations, batch_size=1000, update_conflicts=True,
            unique_fields=["source_id"], update_fields=[
                "name", "aliases", "address", "city", "state", "median_price", "active_dataset", "price_conflict"])
        if changed_locations:
            StationLocation.objects.filter(station_id__in=changed_locations).delete()
        station_ids = dict(FuelStation.objects.filter(
            source_id__in=[s.station_id for s in cleaned.stations]).values_list("source_id", "pk"))
        FuelPrice.objects.bulk_create([FuelPrice(station_id=station_ids[r.station_id],
            dataset=dataset, source_row=r.source_row, source_name=r.name, rack_id=r.rack_id, price=r.price)
            for r in cleaned.records], batch_size=1000)
        dataset.completed = True
        dataset.save(update_fields=["completed"])
    return {"status": "imported", "checksum": checksum, **summary}
