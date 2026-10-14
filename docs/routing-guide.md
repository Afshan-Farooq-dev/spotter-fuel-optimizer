# Routing and fuel optimization

## Run and test

From the repository root:

```powershell
./backend/.venv/Scripts/python.exe backend/manage.py migrate
./backend/.venv/Scripts/python.exe backend/manage.py import_us_boundaries data/reference/cb_2024_us_state_500k.zip
./backend/.venv/Scripts/python.exe backend/manage.py runserver
```

POST http://127.0.0.1:8000/api/routes/optimize/ with JSON:

```json
{
  "start": {"longitude": -95.3698, "latitude": 29.7604},
  "destination": {"longitude": -96.7970, "latitude": 32.7767},
  "initial_fuel_gallons": 50,
  "reserve_gallons": 0
}
```

Start/destination can also be US place/address strings. Fresh textual endpoints
require geocoding calls in addition to directions; explicit coordinates require
none. All coordinates are checked against imported Census polygons. Identical
endpoints, nonfinite coordinates, unknown fields, excessive fuel and invalid
reserves are rejected. The optional corridor_metres is between 100 and 5,000;
the default is 2,000.

The vehicle has fixed 500-mile range, 10 MPG and 50-gallon tank capacity.
Initial fuel defaults to a full tank. Total cost is new fuel purchases only;
historical cost of initial fuel is unknown and excluded. Consequently a trip
under 500 miles with a full tank can have zero purchases and zero expenditure.
Fuel consumed, purchased and remaining are reported separately.

## Response and algorithm

Successful responses include a GeoJSON LineString, provider road distance and
duration, verified fuel-stop points, source/median prices, purchase gallons,
arrival/departure fuel, line costs and total cost. Decimal quantities are strings.
Each purchase payment is rounded to USD cents; total cost is the sum of rounded
purchase payments. Fuel quantities are not rounded before feasibility checks.

The greedy purchase rule buys enough to reach the next cheaper reachable station;
otherwise it fills only to capacity or the remaining trip requirement. An
independent exact dynamic-programming oracle verifies generated routes, and a
separate audit checks conservation, reserve and tank capacity before returning a
successful plan.

Optimization is exact for fuel purchases on the selected station sequence.
Candidate selection uses estimated baseline chainage and a spatial corridor.
The implementation does not claim the globally cheapest road route or all
possible station detours. A provisional reserve provides some detour headroom.
A final ORS route through selected station waypoints supplies actual leg distances;
purchases are recomputed from those distances. If that sequence cannot satisfy
the range, it returns a 422 rather than inventing an access distance.

Fuel stops are routed to ORS's snapped road points. Reported snap offsets are
bounded to 200 meters. Unmapped private driveway access is not modeled as a
verified road leg. The route_waypoint_station_ids field includes any selected
waypoints where recomputation ultimately purchases no fuel.

## Provider calls, caching and speed

- A no-refueling trip normally makes one directions call.
- Refueling normally uses a baseline call and a stop-verification call.
- Positive geometry caches persist in Postgres for 24 hours, independently of
  prices. Current station prices are reread for every plan.
- A cached repeat can use zero directions calls.
- Endpoint geocoding has a persistent 30-day cache.
- Timeout/retry attempts are bounded and included in provider call counts.
- An ORS 429 sets a cooldown and returns Retry-After; it is not immediately retried.
- The default local request rate is 30 requests/minute per client IP.
- A geography GiST index supports ST_DWithin searches in meters.
- Healthy WSGI database connections are reused for up to 60 seconds.

The default Django throttle/cooldown cache is per process. Configure a shared
Django cache for a multi-worker deployment. Geometry cache writes are persistent;
concurrent first misses can still make duplicate provider calls.

The ORS public service has distance and waypoint limits. Requests use
driving-car and avoid country borders. Trips without a connected supported US
driving path can fail. At most 48 selected station stops fit the 50-waypoint
request limit. Alternative routes and truck height/weight restrictions are not
implemented.

## Genuine station enrichment

A local ORS_API_KEY is already configured on this machine and was successfully
used for live verification. On a fresh setup, create a key through the official
ORS account portal and put it only in backend/.env:

```dotenv
ORS_API_KEY=your-personal-key
```

Account portal: https://account.heigit.org/
Directions documentation:
https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/
Geocoder documentation:
https://giscience.github.io/openrouteservice/api-reference/endpoints/geocoder/

```powershell
./backend/.venv/Scripts/python.exe backend/manage.py geocode_stations --state TX --limit 20 --dry-run
./backend/.venv/Scripts/python.exe backend/manage.py geocode_stations --state TX --limit 20
./backend/.venv/Scripts/python.exe backend/manage.py geocode_stations --state TX --limit 20 --retry-unresolved
```

The provider first resolves the source city to focus a 20-km venue search. Those
city centers are search context only: they are never stored as station points.
It then searches the source address and venue name. Cached source-city and raw
station responses avoid repeated calls. A newly encountered locality can add a
third query; subsequent stations in that locality reuse its cache. The bounded
command stops on provider failure, and completed stations remain saved.

Acceptance still requires precise venue/address accuracy, high confidence,
matching source identity, country/state/city metadata, a matching Census state,
and a single distinct coordinate pair. Numbered chain stations cannot be matched
by a generic brand alone. An unmatched or ambiguous point remains null.

**Live coverage limitation:** the tested source-station sample produced no
accepted matches. The dataset's highway-exit descriptions and numbered chain
names do not reliably identify points in the available ORS venue index.
Long live routes currently return insufficient_station_coverage because no
station points have passed validation. This is an explicit data-enrichment
blocker; no coordinates have been fabricated. Successful long/multiple-stop
plans were verified using isolated synthetic provider responses, not production
station data. Full coverage needs further genuine enrichment or an authoritative
station-coordinate source with verified identity matches.

## Verification and Postman

```powershell
./backend/.venv/Scripts/python.exe -m pytest -q --reuse-db
./backend/.venv/Scripts/python.exe backend/manage.py check --database default
./backend/.venv/Scripts/python.exe backend/manage.py makemigrations --check --dry-run
```

Import docs/postman/Spotter-Fuel-Optimizer.postman_collection.json. The collection
contains 10 requests, including short, long, multi-stop and invalid routing
examples. Long/multi-stop examples accept a documented coverage 422 until
genuine station enrichment supplies a reachable sequence. A 503 indicates provider
or configuration failure, not a valid plan.

The Postman desktop runner was not automatically executed. Its request bodies
and equivalent HTTP/response checks were verified. Local live responses are in
data/processed/live_route_verification.json (ignored by Git).

The Census archive is official public geographic data, preserved separately from
the original fuel CSV. Its source URL and SHA-256 are stored on each boundary.
Census source:
https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip
