import csv
import hashlib
import json
import pytest
from apps.stations.services.clean_csv import export_cleaned_data
from apps.stations.services.fuel_data import COLUMNS


def source_csv(tmp_path, name="raw.csv"):
    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        writer.writerows([["1", "Stop", "Road", "Town", "TX", "2", "2.01"],
                         ["1", "Stop", "Road", "Town", "TX", "2", "4.01"]])
    return path


def test_export_is_repeatable_and_preserves_source(tmp_path):
    source = source_csv(tmp_path)
    original = source.read_bytes()
    output = tmp_path / "processed"
    report = export_cleaned_data(source, output)
    first = {p.name: p.read_bytes() for p in output.iterdir()}
    export_cleaned_data(source, output)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == first
    assert source.read_bytes() == original
    assert report["source_sha256"] == hashlib.sha256(original).hexdigest()
    stations = list(csv.DictReader((output / "stations.csv").open()))
    assert stations[0]["median_price"] == "3.01"
    assert json.loads((output / "quality_report.json").read_text())["row_accounting_verified"]


def test_source_cannot_be_overwritten(tmp_path):
    source = source_csv(tmp_path, "stations.csv")
    original = source.read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        export_cleaned_data(source, tmp_path)
    assert source.read_bytes() == original
