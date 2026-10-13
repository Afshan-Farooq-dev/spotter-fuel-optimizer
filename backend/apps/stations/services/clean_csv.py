"""Generate derived CSVs and a quality report without a database connection."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from .fuel_data import clean_fuel_data, read_fuel_csv


def export_cleaned_data(source: Path, output: Path) -> dict:
    source, output = source.resolve(), output.resolve()
    targets = [output / name for name in ("stations.csv", "source_records.csv", "quality_report.json")]
    for target in targets:
        if target == source or (target.exists() and target.samefile(source)):
            raise ValueError("Output must not overwrite the source CSV")
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    result = clean_fuel_data(read_fuel_csv(source))
    if hashlib.sha256(source.read_bytes()).hexdigest() != before:
        raise ValueError("Source changed during processing; rerun with a stable file")
    report = {"schema_version": 1, "source_filename": source.name,
              "source_sha256": before, **result.report}
    output.mkdir(parents=True, exist_ok=True)
    with targets[0].open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["station_id", "name", "aliases_json", "address", "city", "state",
                         "median_price", "source_rows_json", "rack_ids_json", "distinct_prices_json"])
        for station in result.stations:
            writer.writerow([station.station_id, station.name, json.dumps(station.aliases),
                station.address, station.city, station.state, str(station.median_price),
                json.dumps(station.source_rows), json.dumps(station.rack_ids),
                json.dumps([str(p) for p in station.distinct_prices])])
    with targets[1].open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["source_row", "station_id", "name", "address", "city", "state", "rack_id", "price"])
        for record in sorted(result.records, key=lambda r: r.source_row):
            writer.writerow([record.source_row, record.station_id, record.name, record.address,
                             record.city, record.state, record.rack_id, str(record.price)])
    targets[2].write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = export_cleaned_data(args.source, args.output_directory)
    except (ValueError, OSError, csv.Error) as exc:
        print(f"Cleaning failed: {exc}", file=sys.stderr)
        return 1
    summary = {key: report[key] for key in (
        "source_sha256", "total_source_rows", "retained_us_source_rows", "cleaned_us_stations",
        "excluded_canadian_rows", "invalid_rows", "duplicate_us_rows",
        "address_conflict_rows", "price_conflict_station_count", "row_accounting_verified")}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
