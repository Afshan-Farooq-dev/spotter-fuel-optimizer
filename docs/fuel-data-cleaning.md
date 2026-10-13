# Fuel data cleaning policy

## Scope and source preservation

The original `data/raw/fuel-prices-for-be-assessment.csv` is never rewritten.
The cleaner reads UTF-8 (with or without BOM), requires the seven expected
columns, and produces separate derived files. It has no Django, database,
network, or geocoding dependency.

Run from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "backend"
./backend/.venv/Scripts/python.exe -m apps.stations.services.clean_csv data/raw/fuel-prices-for-be-assessment.csv --output-directory data/processed
Remove-Item Env:\PYTHONPATH
```

Generated outputs are ignored by Git and can be recreated:

- `stations.csv`: one resolved row per US station, with median price, aliases,
  rack IDs, distinct prices, and source-row references encoded as JSON columns.
- `source_records.csv`: retained normalized US observations, including original
  CSV row numbers and individual prices.
- `quality_report.json`: source SHA-256, counts, conflict IDs and every excluded
  row's category and reasons.

The source header is row 1; data-row references start at 2. Station and rack IDs
remain strings, including leading zeros. No coordinates are generated.

## Validation and geographic policy

Trim surrounding whitespace in required values and uppercase state/province
codes. Reject missing values, malformed row lengths, nonpositive/nonfinite/
unparseable prices, and IDs that are not positive ASCII digit strings.
Unknown geographic codes are invalid. Explicit US state codes plus DC are
accepted; recognized Canadian provinces/territories are excluded. The supplied
dataset covers 48 US states and has no Alaska or Hawaii records.

Validate first, then exclude Canadian rows, then deduplicate normalized US
records. Duplicates require equality across all seven normalized fields,
including numerically equal Decimal prices. Exclusions have mutually exclusive
categories, so all source rows reconcile.

## Station identity and conflicting prices

Group retained records by OPIS Truckstop ID. If an ID has multiple address/city/
state combinations (case-insensitive address and city), quarantine the entire
station rather than guessing a physical location. Retain distinct names as
aliases; choose the first source name as the display name.

After exact normalized-row deduplication, use the median of all retained
observations for each station. For an even count, use the arithmetic mean of the
two middle prices. Do not deduplicate prices independently: records with distinct
names or rack IDs remain distinct observations and can weight the median.

Use Decimal arithmetic and preserve precision; do not round imported prices to
cents. USD per US gallon is a documented assessment assumption, not metadata
verified from this CSV. Fuel type and observation dates are unspecified.
Median is a deterministic representative price, not necessarily the latest
price, and is not a guarantee of the price available at a station today.

## Verified assessment results

| Category | Count |
| --- | ---: |
| Source rows | 8,151 |
| Canadian rows excluded | 620 |
| Duplicate US rows removed | 26 |
| Invalid rows | 0 |
| Address-conflict rows | 0 |
| Retained US source observations | 7,505 |
| Resolved US stations | 6,626 |
| US station IDs with multiple distinct prices | 487 |

Row reconciliation: **8,151 = 620 + 26 + 7,505**.
The earlier 597 conflicting IDs included Canadian entries; the final 487 count
is scoped to eligible US stations.

A compact machine-readable snapshot is committed as `docs/fuel_data_summary.json`.
The full generated report includes exclusion rows and conflicting station IDs.

## Checks and handoff

Run `./backend/.venv/Scripts/python.exe -m pytest -q` from the repository root.
Checks cover geographic filtering, invalid prices, schema and row lengths,
median precision, aliases, address conflicts, source preservation, output
overwrite protection and deterministic reprocessing.

The database import in Phase 3 should reuse `read_fuel_csv` and
`clean_fuel_data`. This phase does not create station models or write data to
PostgreSQL. Coordinate enrichment is a later phase and must use verified
provider results, never city centers or invented points.
