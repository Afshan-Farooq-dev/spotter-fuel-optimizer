# Spotter Labs Loom demonstration — maximum 4:45

## Prepare before recording

Start Django on 127.0.0.1:8000 and Vite on 127.0.0.1:5173 using the root README. Confirm the local database contains imported prices, Census boundaries and the verified Tomah station; configure the ORS key locally. Import `docs/postman/Spotter-Fuel-Optimizer.postman_collection.json` with base_url=http://127.0.0.1:8000. Open Postman, the frontend and the code files listed below. Keep credential/environment files closed and avoid recording request headers containing provider keys.

Use the known endpoint-coordinate request for the demonstration; place-text searches can be ambiguous. A warmed route is fine, but describe cache hits accurately. Do not clear caches or import new datasets during the recording. Record a genuine API response; if the provider is unavailable, explain the failure rather than replacing it with fabricated output.

## 0:00–0:20 — Introduce the solution

**Show:** Postman collection and project name.

**Say:** “This is my Spotter Labs fuel route optimizer. The Django API accepts US endpoints, returns real road geometry and calculates fuel purchases using the supplied price dataset. The vehicle has a 500-mile range, 10 miles per gallon and a 50-gallon tank. I’ll start with the API, then briefly show the UI and implementation.”

## 0:20–0:40 — Readiness and source data

**Do:** Send **Health check**, then **List stations and capture an ID**. Show the status and one station's price/coordinate metadata.

**Say:** “The health endpoint checks database readiness. Station responses expose source identity, median price and coordinate status. The original CSV is preserved, Canadian rows and exact duplicates are handled, and conflicting station prices use an auditable median.”

## 0:40–1:55 — Main Postman demonstration

**Do:** Select **Verified refueling: Indianapolis to Minneapolis**. Show POST `/api/routes/optimize/`, its raw JSON endpoint coordinates, and the full-tank input default. Click **Send**. Show HTTP status, then geometry.type and these response fields: distance_miles, fuel_stops, price_per_gallon, gallons_purchased, total_cost, arrival/departure fuel and provider_usage. Show the Tests results if the four assertions pass.

**Say:** “This route uses actual coordinates for both endpoints. In the recorded verification it covered about 595 miles, so a full tank cannot finish it without buying fuel. The stop is Kwik Trip number 796 in Tomah, matched to an actual mapped fuel facility. The response reports the price, gallons purchased, purchase cost and fuel balance.”

**Continue, using the values actually returned:** “The verified run purchased about 9.52 gallons for $31.30. That is new expenditure only; the historical cost of the initial fuel is excluded. The optimizer checks tank capacity and actual driving legs through the stop. Geometry is a GeoJSON LineString ready for the map.”

**Do:** Send once more and show provider_usage.

**Say:** “The repeat reuses cached directions while prices are read separately. A cold refueling request normally needs two directions calls: the baseline and the final route through stops. I chose the extra call to verify real detours and reachability instead of treating estimated distances as final.”

## 1:55–2:30 — Honest limits and input validation

**Do:** Send **Optimize a long US route** (Houston to Chicago). Show the actual 422 insufficient-coverage response. Then send **Reject a non-US endpoint**, showing its 400 response. If a provider error appears instead, state its actual status and move on.

**Say:** “Coverage is deliberately conservative. Currently one station has verified coordinates, and 6,625 lack verified coordinates; this is not nationwide coverage. When verified stops cannot support a route, the API reports that limitation rather than inventing coordinates or allowing a leg beyond the vehicle's range. US endpoints are also validated against Census state polygons.”

## 2:30–3:00 — Brief frontend demonstration

**Do:** Open the frontend and click **Load verified route**. Show the route summary, map, fuel stop and itinerary. Click **Locate on map**. Keep this segment short.

**Say:** “The React workspace uses the same API. The shortcut sets endpoint coordinates only. Distance, stops, gallons and cost all come from the response. Selecting a stop connects its purchase card to the map. The layout is responsive, and coverage errors offer a clear recovery path.”

## 3:00–4:10 — Quick code overview

**Show in order:**

1. `backend/apps/routes/api/serializers.py` — input validation and configurable starting fuel/reserve.
2. `backend/apps/routes/services/planning.py` — endpoint resolution, route cache, station selection, final driving verification and response assembly.
3. `backend/apps/routes/services/candidates.py` — indexed PostGIS corridor selection using verified stations.
4. `backend/apps/routes/services/optimizer.py` and `audit.py` — fuel purchase decisions and independent conservation/capacity checks.
5. `backend/apps/stations/services/importing.py` and `osm_enrichment.py` — repeatable imports, original price observations and conservative identity matching/provenance.

**Say:** “The API layer is small, and provider transport, spatial selection and fuel planning are separate services. The greedy purchase algorithm is optimal for a fixed station sequence; I do not claim a globally optimal road path across every possible detour. An independent audit checks the returned fuel balance.”

**Continue:** “Imports are transactional and checksum-based, retain source observations and use Decimal prices. Enrichment is cached and resumable, accepts sufficiently verified identities, records OSM provenance and never substitutes city centers. Provider failures and rate limits are handled without exposing keys.”

## 4:10–4:45 — Verification and close

**Show:** README verification/limitations section and repository structure. Do not rerun test suites during the video.

**Say:** “The existing verification passed 96 backend tests, three live desktop/mobile browser tests and the production build. The browser checks cover mapping, itinerary interactions, JSON export and recovery from an actual coverage failure. The README includes setup steps, API examples and the Postman collection.”

**Finish:** “Remaining work is broader trustworthy coordinate coverage and frontend optimization. Vite warns about a roughly 510-kilobyte main bundle, and two generated shadcn exports produce fast-refresh lint warnings; there are no lint errors. The current assessment demonstrates a real refueling journey end to end while making the coverage limitation explicit. Thank you.”

**Stop recording by 4:45.** If running behind, skip the station-list request, repeated route request or frontend segment. Preserve the primary Postman optimization result, coverage disclosure and code overview. Upload/share the Loom recording yourself; this script does not create or publish a video.
