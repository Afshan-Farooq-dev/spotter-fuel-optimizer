# Backend imports, geocoding and station API

## Phase 3: database models and import

- FuelDataset: source checksum, import completion marker and full cleaning report.
- FuelStation: stable source ID, normalized identity, aliases, current median price and active dataset.
- FuelPrice: retained source observation, rack ID, CSV row number and dataset provenance.
- StationLocation: nullable PostGIS WGS84 Point with provider, match status and metadata.
- GeocodingCache: normalized query identity, raw provider response and fetch time.

Prices use Decimal fields with 18 total digits and 10 fractional digits. Unsupported
precision or oversized IDs fail before database writes instead of silently rounding.
The supplied CSV prices and their even-count medians fit this precision.

From the repository root:

```powershell
./backend/.venv/Scripts/python.exe backend/manage.py migrate
./backend/.venv/Scripts/python.exe backend/manage.py import_fuel_prices data/raw/fuel-prices-for-be-assessment.csv --dry-run
./backend/.venv/Scripts/python.exe backend/manage.py import_fuel_prices data/raw/fuel-prices-for-be-assessment.csv
```

The dry-run validates and summarizes without database writes. Imports reuse the
Phase 2 cleaning policy. Writes use one transaction, an advisory lock to serialize
imports, bulk station upserts and bulk price inserts. The SHA-256 completion marker
makes repeated imports of the same bytes a no-op. Database constraints additionally
prevent duplicate source rows and nonpositive prices.

A different file creates a new snapshot and updates the affected stations' active
median prices; earlier observations remain available. Stations absent from the new
snapshot retain their previous dataset, rather than being silently deleted.
Changed station addresses invalidate existing location records. Geocoding never
occurs during import.

Verified assessment import: **6,626 stations, 7,505 source price observations,
one completed dataset**. Repeating the command returns `already_imported`.
All station medians were compared with the pure cleaner and matched.

## Phase 4: geocoding preparation

No coordinates are derived from addresses or city centers locally.
The opt-in adapter uses openrouteservice's Pelias geocoder:
https://giscience.github.io/openrouteservice/api-reference/endpoints/geocoder/

Set a personal `ORS_API_KEY` in the ignored local `backend/.env` to make live calls.
Check your account's current quotas and attribution requirements before bulk use.
The application does not ship a key and implementation verification made no external
geocoding calls.

```powershell
./backend/.venv/Scripts/python.exe backend/manage.py geocode_stations --limit 10 --dry-run
./backend/.venv/Scripts/python.exe backend/manage.py geocode_stations --limit 10
./backend/.venv/Scripts/python.exe backend/manage.py geocode_stations --station-id 1 --dry-run
```

Batch size defaults to 10 and is capped at 100. Default runs resume with stations
having no location record. Use `--retry-unresolved` for prior unresolved results,
or `--refresh` to request fresh results. Station IDs are internal database IDs.

The adapter applies request timeouts, spacing between calls and bounded retries
for transient failures. A provider failure stops the command, leaving prior
completed stations saved and the failed station eligible for a retry. Credentials
are transmitted through request headers and are never included in error messages.

Raw valid responses, including empty and ambiguous results, are cached for 30 days
by normalized name/address/city/state, provider identity and endpoint. Provider
errors are not cached. A refreshed or expired cache is replaced.

Accepted coordinates must have all of the following:

- finite, valid WGS84 longitude and latitude in GeoJSON order;
- provider country code USA and a matching station state and city;
- plausible bounds for the continental US, Alaska or Hawaii;
- confidence of at least 0.9 and point accuracy;
- a venue matching a station name/alias, or an address matching the source address;
- one distinct accepted coordinate pair.

The status `verified` means these provider-validation criteria passed, not a
manual site survey. Country/state membership relies on provider metadata; coarse
bounds are only a plausibility check, not exact administrative polygons. Route
accessibility is not validated in this phase. Strict matching may leave highway
exit addresses unresolved; that is preferable to assigning an uncertain point.

Coordinates remain null for no-match/ambiguous results. No station in the
development database has been geocoded yet. Synthetic coordinates exist only in
isolated test responses and have not been imported into the development database.

## REST API

Start the development server:

```powershell
./backend/.venv/Scripts/python.exe backend/manage.py runserver
```

| Method and path | Behavior |
| --- | --- |
| GET /api/health/ | 200 with database readiness; 503 if the database is unavailable |
| GET /api/stations/ | Read-only paginated station list |
| GET /api/stations/{id}/ | Station detail using its internal integer ID; 404 if absent |

List parameters: `state=TX`, `source_id=20`, `geocoded=true|false`,
`search=Houston`, `page=2`, `page_size=25`. States are case-insensitive.
Invalid state/geocoded values return 400. Page size defaults to 25 and is capped
at 100. Results have stable ascending ID ordering.

List responses contain `count`, `next`, `previous` and `results`. Station
responses include identity, aliases, Decimal median price as a string, price-conflict
flag, dataset checksum and location status. Unresolved stations return null
coordinates. Currency/unit/method fields expose the documented USD-per-US-gallon
median assumption. Reads perform no external calls; the list uses two SQL queries
with related dataset/location data selected together. Write methods are not exposed.

## Essential verification

An isolated PostGIS database is used for tests. On a fresh machine, create
`test_spotter_fuel` owned by `spotter_app` and enable PostGIS as the administrator.
The application role does not need superuser or database-creation privileges.

```sql
CREATE DATABASE test_spotter_fuel OWNER spotter_app;
```

Connect to that test database as the administrator, then:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Run from the repository root:

```powershell
./backend/.venv/Scripts/python.exe -m pytest -q --reuse-db
./backend/.venv/Scripts/python.exe backend/manage.py check --database default
./backend/.venv/Scripts/python.exe backend/manage.py makemigrations --check --dry-run
```

DB_TEST_NAME optionally overrides the test database name. Keep the test database
separate from spotter_fuel; pytest rolls back test data. Tests cover import
idempotence/rollback/history, geocoder validation/cache/errors and API behavior,
pagination and query count. Provider responses are mocked.

Live HTTP checks were run against development PostGIS for health/list/detail,
state filtering, 404 and invalid-state 400. A local generated verification report
is available at `data/processed/backend_verification.json`. The temporary
verification server is stopped afterward.

The Postman collection is available in `docs/postman/`; see its README for import
and runner instructions. Route optimization is now implemented; see routing-guide.md for its API and current coverage limitations. Frontend features are not implemented.
