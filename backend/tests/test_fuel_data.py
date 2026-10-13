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
