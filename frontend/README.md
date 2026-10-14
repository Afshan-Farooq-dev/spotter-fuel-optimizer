# Spotter frontend

React + Vite + Tailwind CSS + shadcn/ui + Leaflet. All route geometry, fuel stops and calculated metrics come from Django. Design references are documented in ../docs/frontend-design.md.

## Run locally

In PowerShell terminal 1, from the repository root:

```powershell
cd E:\spotter-fuel-optimizer
.\backend\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000
```

In terminal 2:

```powershell
cd E:\spotter-fuel-optimizer\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173 and click **Load verified route**. Dependencies are already installed locally, so npm ci is only needed on a fresh checkout or to reproduce the lockfile.

The location fields accept US place/address text or exact coordinates in **latitude, longitude** order. Text searches may be rejected as ambiguous; coordinates avoid an extra geocoding request and are still validated by Django's US boundaries. The verified shortcut supplies endpoint coordinates only; calculated results are never embedded in the frontend.

## Checks

Keep Django running, then:

```powershell
npm run build
npm run lint
npx playwright test
```

Browser tests use installed Microsoft Edge and start Vite automatically if needed. Tests require the imported fuel dataset, verified Tomah station, state boundaries and configured backend ORS key. Playwright results/traces and screenshots are ignored by Git. Production deployment must proxy /api to Django on the same origin; Vite's development proxy is not a production server. Never put ORS credentials in frontend environment variables.

## Verified results

On 14 October 2026, all three live browser tests passed in one run: desktop route/markers/itinerary/JSON export; mobile layout without horizontal overflow; and actual insufficient-coverage handling followed by recovery to the verified route. The verified response was 595.205 miles, one real stop and $31.30 in fuel purchases, with cached directions. Desktop tiles loaded successfully. A production build passed. Lint has two generated shadcn fast-refresh export warnings; the production build warns that the current bundle exceeds 500 kB. These are remaining optimization items, not failed integration checks.

Known coverage limitation: only one station currently has verified coordinates. This supports the demonstrated Indianapolis-to-Minneapolis journey, not nationwide coverage. Coverage failures are displayed without invented routes, stops or costs. Directions are driving-car routes, not truck-clearance routing. Prices are assessment CSV medians, not live pump prices.
