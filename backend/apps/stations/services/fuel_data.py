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
