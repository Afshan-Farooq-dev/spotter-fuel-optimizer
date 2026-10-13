"""Pure CSV validation; no Django, database, or network dependencies."""
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

COLUMNS = ("OPIS Truckstop ID", "Truckstop Name", "Address", "City", "State", "Rack ID", "Retail Price")
US_STATES = frozenset("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())
CANADIAN_PROVINCES = frozenset("AB BC MB NB NL NS NT NU ON PE QC SK YT".split())


@dataclass(frozen=True)
class FuelRecord:
    source_row: int
    station_id: str
    name: str
    address: str
    city: str
    state: str
    rack_id: str
    price: Decimal


@dataclass
class ValidationResult:
    records: list[FuelRecord]
    total_rows: int
    exclusions: list[dict]


def read_fuel_csv(path: Path) -> ValidationResult:
    """Normalize whitespace, retain identifiers as strings, and classify every row."""
    records, exclusions = [], []
    total = 0
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or len(reader.fieldnames) != len(COLUMNS) or set(reader.fieldnames) != set(COLUMNS):
            raise ValueError("CSV must contain exactly the seven expected fuel-price columns")
        for source_row, raw in enumerate(reader, start=2):
            total += 1
            values = {key: (raw.get(key) or "").strip() for key in COLUMNS}
            values["State"] = values["State"].upper()
            reasons = []
            if None in raw or any(raw.get(key) is None for key in COLUMNS):
                reasons.append("malformed_row")
            if any(not values[key] for key in COLUMNS):
                reasons.append("missing_required_value")
            for key in ("OPIS Truckstop ID", "Rack ID"):
                value = values[key]
                if not value.isascii() or not value.isdecimal() or not value.strip("0"):
                    reasons.append("invalid_" + ("station_id" if key == "OPIS Truckstop ID" else "rack_id"))
            try:
                price = Decimal(values["Retail Price"])
                if not price.is_finite() or price <= 0:
                    reasons.append("invalid_price")
            except InvalidOperation:
                price = None
                reasons.append("invalid_price")
            state = values["State"]
            if state not in US_STATES and state not in CANADIAN_PROVINCES:
                reasons.append("unknown_state_or_province")
            if reasons:
                exclusions.append({"source_row": source_row, "category": "invalid", "reasons": reasons})
            elif state in CANADIAN_PROVINCES:
                exclusions.append({"source_row": source_row, "category": "canadian", "reasons": ["outside_us"]})
            else:
                records.append(FuelRecord(source_row, values["OPIS Truckstop ID"],
                    values["Truckstop Name"], values["Address"], values["City"],
                    state, values["Rack ID"], price))
    return ValidationResult(records, total, exclusions)

@dataclass(frozen=True)
class CleanStation:
    station_id: str
    name: str
    aliases: tuple[str, ...]
    address: str
    city: str
    state: str
    median_price: Decimal
    source_rows: tuple[int, ...]
    rack_ids: tuple[str, ...]
    distinct_prices: tuple[Decimal, ...]


@dataclass
class CleaningResult:
    stations: list[CleanStation]
    records: list[FuelRecord]
    report: dict


def clean_fuel_data(result: ValidationResult) -> CleaningResult:
    """Deduplicate normalized US records, quarantine address conflicts, then take medians."""
    from collections import Counter, defaultdict
    from statistics import median

    exclusions = list(result.exclusions)
    seen, groups = set(), defaultdict(list)
    for record in result.records:
        identity = (record.station_id, record.name, record.address, record.city,
                    record.state, record.rack_id, record.price)
        if identity in seen:
            exclusions.append({"source_row": record.source_row, "category": "duplicate",
                               "reasons": ["duplicate_normalized_us_row"]})
        else:
            seen.add(identity)
            groups[record.station_id].append(record)
    stations, retained, address_conflicts, price_conflicts = [], [], [], []
    for station_id in sorted(groups, key=lambda value: (int(value), value)):
        records = groups[station_id]
        addresses = {(r.address.casefold(), r.city.casefold(), r.state) for r in records}
        if len(addresses) != 1:
            address_conflicts.append(station_id)
            exclusions.extend({"source_row": r.source_row, "category": "address_conflict",
                               "reasons": ["station_id_has_conflicting_addresses"]} for r in records)
            continue
        first = records[0]
        prices = tuple(sorted({r.price for r in records}))
        if len(prices) > 1:
            price_conflicts.append(station_id)
        stations.append(CleanStation(station_id, first.name, tuple(sorted({r.name for r in records})),
            first.address, first.city, first.state, median([r.price for r in records]),
            tuple(r.source_row for r in records), tuple(sorted({r.rack_id for r in records})), prices))
        retained.extend(records)
    exclusions.sort(key=lambda item: item["source_row"])
    counts = Counter(item["category"] for item in exclusions)
    assert result.total_rows == len(retained) + len(exclusions)
    report = {
        "total_source_rows": result.total_rows,
        "retained_us_source_rows": len(retained),
        "cleaned_us_stations": len(stations),
        "excluded_canadian_rows": counts["canadian"],
        "invalid_rows": counts["invalid"],
        "duplicate_us_rows": counts["duplicate"],
        "address_conflict_rows": counts["address_conflict"],
        "address_conflict_station_ids": address_conflicts,
        "price_conflict_station_count": len(price_conflicts),
        "price_conflict_station_ids": price_conflicts,
        "represented_us_states": sorted({s.state for s in stations}),
        "median_price_min": str(min((s.median_price for s in stations), default="")),
        "median_price_max": str(max((s.median_price for s in stations), default="")),
        "price_policy": "Median of valid normalized US rows after exact normalized-row deduplication; prices are not deduplicated independently.",
        "currency_assumption": "USD",
        "price_unit_assumption": "US gallon",
        "fuel_type": "unspecified in source",
        "row_accounting_verified": True,
        "exclusions": exclusions,
    }
    return CleaningResult(stations, retained, report)
