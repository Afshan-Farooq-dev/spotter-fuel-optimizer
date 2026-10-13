import csv
from decimal import Decimal
import pytest
from apps.stations.services.fuel_data import COLUMNS, read_fuel_csv


def write_csv(tmp_path, rows, columns=COLUMNS):
    path = tmp_path / "fuel.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)
    return path


def row(price="3.00733333", state="TX", station_id="001"):
    return [station_id, "Station", "I-10 EXIT 1", "Town", state, "307", price]


def test_us_canada_and_invalid_rows_reconcile(tmp_path):
    rows = [row(), row(state="ON"), row(price="NaN"), row(price="-1"), row(state="ZZ"), row(station_id="bad")]
    result = read_fuel_csv(write_csv(tmp_path, rows))
    assert result.total_rows == len(result.records) + len(result.exclusions) == 6
    assert len(result.records) == 1
    assert result.records[0].station_id == "001"
    assert result.records[0].price == Decimal("3.00733333")
    assert [x["category"] for x in result.exclusions] == ["canadian"] + ["invalid"] * 4


@pytest.mark.parametrize("price", ["0", "Infinity", "-Infinity", "abc", ""])
def test_invalid_prices(tmp_path, price):
    assert read_fuel_csv(write_csv(tmp_path, [row(price=price)])).exclusions


def test_whitespace_and_state_normalization(tmp_path):
    result = read_fuel_csv(write_csv(tmp_path, [row(state=" tx ")]))
    assert result.records[0].state == "TX"


def test_bad_schema_fails(tmp_path):
    with pytest.raises(ValueError, match="seven expected"):
        read_fuel_csv(write_csv(tmp_path, [], columns=["State"]))


def test_malformed_row_is_rejected(tmp_path):
    result = read_fuel_csv(write_csv(tmp_path, [row() + ["extra"]]))
    assert "malformed_row" in result.exclusions[0]["reasons"]

from apps.stations.services.fuel_data import clean_fuel_data


def test_duplicates_do_not_weight_median(tmp_path):
    result = clean_fuel_data(read_fuel_csv(write_csv(tmp_path, [row(price="2"), row(price="2"), row(price="4")])))
    assert result.stations[0].median_price == Decimal("3")
    assert result.report["duplicate_us_rows"] == 1
    assert result.report["price_conflict_station_count"] == 1
    assert result.stations[0].source_rows == (2, 4)


def test_median_preserves_decimal_precision(tmp_path):
    result = clean_fuel_data(read_fuel_csv(write_csv(tmp_path, [row(price="3.00000001"), row(price="3.00000002")])))
    assert result.stations[0].median_price == Decimal("3.000000015")


def test_aliases_are_preserved_without_deduplicating_price_observations(tmp_path):
    alias = row(price="2")
    alias[1] = "Alternate station name"
    result = clean_fuel_data(read_fuel_csv(write_csv(tmp_path, [row(price="2"), alias, row(price="4")])))
    assert result.stations[0].median_price == Decimal("2")
    assert len(result.stations[0].aliases) == 2


def test_conflicting_addresses_are_quarantined(tmp_path):
    conflict = row()
    conflict[2] = "A different road"
    result = clean_fuel_data(read_fuel_csv(write_csv(tmp_path, [row(), conflict])))
    assert result.stations == []
    assert result.report["address_conflict_rows"] == 2
    assert result.report["address_conflict_station_ids"] == ["001"]


def test_input_is_not_mutated_and_repeated_cleaning_matches(tmp_path):
    source = write_csv(tmp_path, [row(), row(state="ON"), row(price="4")])
    original = source.read_bytes()
    validated = read_fuel_csv(source)
    a, b = clean_fuel_data(validated), clean_fuel_data(validated)
    assert a == b
    assert source.read_bytes() == original
    assert len(validated.exclusions) == 1
