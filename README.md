# Spotter Fuel Optimizer

Django REST Framework backend for the Spotter Labs assessment. The stations and routes apps are scaffolded. CSV cleaning, transactional database imports, cached geocoding preparation and read-only station APIs are implemented. Route geometry, fuel purchase optimization and the POST routing API are implemented. Live long-route success requires verified station coordinate coverage; the frontend is not implemented.

## Local development on Windows

Python 3.12, PostgreSQL 16 and PostGIS are used locally. Install the compatible PostGIS bundle using Stack Builder. Enable the extension in the application database as the PostgreSQL administrator:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Create a dedicated application role and make it the database owner. The Django application uses `spotter_app`, not the PostgreSQL superuser.

From the repository root in PowerShell:

```powershell
py -3.12 -m venv backend/.venv
./backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

Copy the environment example only on a fresh setup; do not overwrite an existing `.env`. Generate a Django secret, supply the database password, and adapt the optional Windows GIS DLL paths to the installed bundle. `.env`, its backups, and `.env.postgres-admin` are local ignored files and must never be committed or shared.

```powershell
./backend/.venv/Scripts/python.exe backend/manage.py check --database default
./backend/.venv/Scripts/python.exe backend/manage.py migrate
./backend/.venv/Scripts/python.exe backend/manage.py runserver
```

The development server runs at http://127.0.0.1:8000/. Health is at `/api/health/`, stations at `/api/stations/`, and station detail at `/api/stations/{id}/`. The admin login is at `/admin/login/`; no administrator account is created automatically. A 404 at the root URL is expected.

See [backend import, geocoding and API instructions](docs/backend-api.md).

## Data

The original assessment CSV is preserved unchanged in `data/raw/fuel-prices-for-be-assessment.csv`. It contains 8,151 rows. The cleaner produces 6,626 US stations using documented median-price assumptions. See [the cleaning policy](docs/fuel-data-cleaning.md) for commands and verified counts. Station coordinate enrichment is a subsequent phase; no station coordinates have been invented.

## Windows PostGIS repair

The local installation contained a `libxml2-2.dll` requiring an absent `liblzma-5.dll`. Restoring the XML DLL from the matching official PostgreSQL 16 / PostGIS 3.4.2 archive resolved extension loading. The prior DLL was backed up outside the repository before replacement. Avoid downloading standalone DLLs from unofficial sites.

Django reads optional `GIS_LIBRARY_DIRECTORY`, `GDAL_LIBRARY_PATH` and `GEOS_LIBRARY_PATH` from `.env`. On Windows, the configured DLL directory is added to the process search paths. Other platforms can omit these variables and use their system GIS libraries.

## Verification

Run `./backend/.venv/Scripts/python.exe -m pytest -q --reuse-db` after preparing the isolated PostGIS test database as described in the backend instructions.

## Postman and final checks

Import [the Postman collection](docs/postman/Spotter-Fuel-Optimizer.postman_collection.json), start Django, and run requests in order. [Postman instructions](docs/postman/README.md) explain the automatic station ID capture.

See [actual final verification results and remaining assessment scope](docs/final-verification.md).

## Routing phase

See [routing setup, API contract, provider budgets and live coverage limitations](docs/routing-guide.md). `POST /api/routes/optimize/` accepts US endpoints and returns a fuel plan when genuine station coverage is sufficient. A real short route and cached repeat were verified; long/multi-stop calculations are verified in isolated tests, while live station enrichment remains a data blocker.
