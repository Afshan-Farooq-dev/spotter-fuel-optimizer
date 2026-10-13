# Spotter Fuel Optimizer

Django REST Framework backend for the Spotter Labs assessment. The stations and routes apps are scaffolded; fuel imports, API endpoints, route optimization and the frontend are not implemented yet.

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

The development server runs at http://127.0.0.1:8000/. The admin login is at `/admin/login/`; no administrator account is created automatically. A 404 at the root URL is expected until public endpoints are added.

## Data

The original assessment CSV is preserved unchanged in `data/raw/fuel-prices-for-be-assessment.csv`. It contains 8,151 rows. Data cleaning and station coordinate enrichment are subsequent phases; no station coordinates have been invented.

## Windows PostGIS repair

The local installation contained a `libxml2-2.dll` requiring an absent `liblzma-5.dll`. Restoring the XML DLL from the matching official PostgreSQL 16 / PostGIS 3.4.2 archive resolved extension loading. The prior DLL was backed up outside the repository before replacement. Avoid downloading standalone DLLs from unofficial sites.

Django reads optional `GIS_LIBRARY_DIRECTORY`, `GDAL_LIBRARY_PATH` and `GEOS_LIBRARY_PATH` from `.env`. On Windows, the configured DLL directory is added to the process search paths. Other platforms can omit these variables and use their system GIS libraries.
