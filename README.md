# Spotter Fuel Optimizer

A Django REST API and React map workspace for the Spotter Labs assessment. It returns actual US driving geometry, selects verified fuel stops, and calculates fuel purchases using the supplied CSV. The vehicle has a **500-mile range, 10 MPG and a 50-gallon tank**.

## Backend setup

Verified locally with Python 3.12, PostgreSQL 16/PostGIS, and the pinned packages in `backend/requirements.txt`. Install PostgreSQL, its compatible PostGIS bundle, and native GDAL/GEOS/PROJ libraries. Create an application database owned by a dedicated non-superuser role; enable `CREATE EXTENSION IF NOT EXISTS postgis;` in that database as an administrator.

From the repository root in PowerShell, on a fresh checkout:

```powershell
py -3.12 -m venv backend/.venv
./backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

Do not overwrite an existing `.env`. Set a generated `DJANGO_SECRET_KEY`, database connection values and your `ORS_API_KEY` locally. Adapt or omit the Windows GIS library paths for your installation. The ORS key is required for uncached live routing and geocoding and stays on the backend.

```powershell
./backend/.venv/Scripts/python.exe backend/manage.py migrate
./backend/.venv/Scripts/python.exe backend/manage.py import_fuel_prices data/raw/fuel-prices-for-be-assessment.csv
./backend/.venv/Scripts/python.exe backend/manage.py import_us_boundaries data/reference/cb_2024_us_state_500k.zip
./backend/.venv/Scripts/python.exe backend/manage.py enrich_osm_stations --file data/reference/osm/tomah-fuel.json --state WI --limit 100
./backend/.venv/Scripts/python.exe backend/manage.py check --database default
./backend/.venv/Scripts/python.exe backend/manage.py runserver 127.0.0.1:8000
```

The imports are repeatable. The OSM source snapshot reproduces the verified Tomah station; broader coverage requires additional trustworthy source data. Database/native GIS and isolated test database details: [backend guide](docs/backend-api.md).

## Frontend setup

Use Node.js 24 (the verified local version). In a second PowerShell terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173/** and click **Load verified route**. React, Vite, Tailwind CSS, shadcn/ui and Leaflet render the backend's geometry, fuel summary and station itinerary. Location inputs accept US place text or `latitude, longitude`; exact coordinates avoid ambiguous geocoding. The example supplies only endpoints, not calculated results.

Vite proxies `/api` to Django on port 8000. Production requires a same-origin reverse proxy to Django and static hosting for the frontend build; Vite's development proxy is not a production service. Never expose ORS credentials through frontend environment variables. [Frontend instructions](frontend/README.md) · [design references](docs/frontend-design.md).

## API

Development base URL: `http://127.0.0.1:8000`. No authentication is configured for this assessment.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health/` | Database readiness |
| GET | `/api/stations/` | Paginated prices, identity and coordinate status |
| GET | `/api/stations/{id}/` | Station detail using its internal integer ID |
| POST | `/api/routes/optimize/` | Driving geometry and fuel purchase plan |

Station filters include `state`, `source_id`, `geocoded`, `search`, `page` and `page_size` (maximum 100).

Verified route request, sent as JSON:

```json
{
  "start": {"longitude": -86.1581, "latitude": 39.7684},
  "destination": {"longitude": -93.265, "latitude": 44.9778},
  "initial_fuel_gallons": 50,
  "reserve_gallons": 0
}
```

Start/destination can also be US place strings. Optional `corridor_metres` accepts 100–5000. API coordinate objects and GeoJSON use **longitude, latitude**, unlike the frontend's typed coordinate input. Responses include LineString geometry, distance/duration, station coordinates and prices, gallons purchased, per-stop costs, total cost and provider call counts. Prices and accounting quantities use decimal strings.

Invalid inputs/non-US endpoints return 400; insufficient verified coverage or infeasible fuel legs return 422; provider/database failures return safe errors (normally 503). Request throttling returns 429. See [routing guide](docs/routing-guide.md) and [optimization contract](docs/routing-contract.md).

## Postman demonstration

Import [Spotter-Fuel-Optimizer.postman_collection.json](docs/postman/Spotter-Fuel-Optimizer.postman_collection.json). Set `base_url` to `http://127.0.0.1:8000`. The 11 requests include health, station APIs, optimization scenarios and **Verified refueling: Indianapolis to Minneapolis**, whose assertions require HTTP 200 and a genuine fuel stop. Run the station list before station detail to capture an ID.

[Postman instructions](docs/postman/README.md) · [Loom demonstration script, 4:45 maximum](docs/loom-demo-script.md).

## Data, accuracy and coverage limits

- The original 8,151-row CSV is preserved unchanged. Cleaning produces 6,626 US stations and 7,505 retained price observations, excluding Canadian entries and exact duplicates. Conflicting prices use a documented median; prices are supplied USD-per-US-gallon observations, **not live pump prices**.
- **1 station is verified; 6,625 currently lack verified coordinates.** This includes unattempted/rejected entries, not proof that the businesses are absent. Nationwide coverage is incomplete; some long routes correctly return 422. No station coordinates or city centers are invented.
- The verified Indianapolis–Minneapolis response covered **595.205 miles**, with a stop at Kwik Trip #796 in Tomah, buying **9.5205 gallons for $31.30**. These are recorded results, not fixed application values. The cold request used two live ORS directions calls; a repeat reused both cached geometries.
- The published OSM point is an actual fuel-facility boundary vertex, not a surveyed driveway entrance. The demonstrated ORS road snap was 5.13 metres. OSM coordinate sources require attribution and applicable ODbL obligations; [provenance and enrichment policies](docs/station-enrichment.md) explain source verification and limitations.
- Initial fuel defaults to a full tank. Expenditure includes **new purchases only**, excluding the historical cost of starting fuel. A short trip can therefore cost zero additional purchases. Optional reserve is enforced.
- Fuel optimization is optimal for a fixed selected station sequence, not globally optimal over every possible road path/detour. Actual final driving legs and fuel conservation are checked. Driving-car directions do not guarantee truck clearance or access.
- Direction and geocoding caches reduce provider calls. Stops normally require a second directions call to validate real detours; one-call routing is used when no refueling is needed. Live provider quotas and availability remain external constraints.

[Cleaning policy](docs/fuel-data-cleaning.md) · [actual route evidence](docs/station-enrichment-verification.json).

## Verification and remaining warnings

Existing checks passed: **96 backend tests**, Django checks, **3 live desktop/mobile browser tests**, and the frontend production build. The collection's verified request also passed four assertions through its HTTP harness; the full Postman desktop runner was not automated. Final documentation preparation did not rerun browser tests or rebuild.

For future verification, with the dedicated PostGIS test database prepared and Django running where needed:

```powershell
./backend/.venv/Scripts/python.exe -m pytest -q --reuse-db
cd frontend
npm run build
npm run lint
npx playwright test
```

Remaining non-blocking warnings: Vite's main JavaScript bundle is about **509.69 kB minified / 158.16 kB gzip**, exceeding its 500 kB warning threshold; map code splitting is a future optimization. Lint reports two fast-refresh export warnings in generated shadcn `button.tsx` and `badge.tsx`, with no lint errors.

Environment files, virtual environments, dependencies, build output, logs, derived data and browser artifacts are excluded from Git. Keep secrets local. Git history is preserved; no submission push has been performed.
