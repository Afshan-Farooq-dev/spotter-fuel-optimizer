# Station coordinate enrichment

Verified on 14 October 2026: **1 of 6,626 US stations** has verified coordinates; **6,625 lack verified coordinates**. These remaining stations include unattempted, rejected and ambiguous records, not 6,625 proven absent businesses. Nationwide routing coverage remains incomplete.

## Sources and policies

OpenStreetMap is the coordinate source under [ODbL](https://www.openstreetmap.org/copyright). Preserve attribution and source identity; distribute adapted coordinate databases under applicable ODbL share-alike requirements. Location evidence is stored separately from the original fuel CSV and prices. An OSM match is evidence of a mapped facility, not a current business inspection or truck access guarantee.

[Overpass policy](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html) favors modest cached queries. This command makes one bounded regional request, declares 25 seconds/32 MiB, limits downloaded responses to 16 MiB, caches successful extracts for 30 days and stops on errors. HTTP 429/502/503/504 cooldowns persist in the database, including Retry-After seconds when provided. Run one enrichment worker; space regional requests by at least 10 seconds. Do not use public Overpass as the online route API backend. For substantial coverage, use regional OSM extracts or your own Overpass deployment.

The default public endpoint returned HTTP 406 for both POST and GET here. A manually tested alternate endpoint timed out. No automatic mirror rotation or repeated retries were used. The [OSM editing API policy](https://operations.osmfoundation.org/policies/api/) discourages read-only bulk projects. Two small diagnostic map/object downloads established the Tomah match; the reusable pipeline does not call that editing API. Obtain future batches through Overpass or licensed offline extracts.

The [official Kwik Trip store list](https://www.kwiktrip.com/Maps-Downloads/Store-List) confirms branch 796, Tomah, WI, 310 E McCoy Blvd. Its publicly published coordinate is near a different mapped BP facility; it was **not imported**. The [official truck-friendly listing](https://www.kwiktrip.com/wordpress/wp-content/uploads/2026/01/Truck-Friendly-2026.pdf) corroborates branch 796. [Wisconsin DOT](https://wisconsindot.gov/Documents/projects/multimodal/wevi-round-15-awarded-locations.pdf) also corroborates its street address. Official locator pages are useful corroboration, but public visibility does not establish a bulk redistribution license. No proprietary locator coordinate database was scraped or redistributed. Pilot's current locator shows a different Gila Bend branch number from an older CSV entry; that was not silently matched.

## Matching

Require active amenity=fuel plus exact city/state and either:

- Exact chain brand and store number parsed from the CSV station name; or
- Exact station name and street address, or an explicit matching OPIS reference.

Explicit conflicting OPIS references or highway exit tags reject the match. Store number and OPIS ID are different identifiers. Highway-only CSV addresses cannot be matched to city centers or generic chain venues. Missing exit information is not inferred. Abbreviated street addresses and alternate municipality names currently require further corroboration rather than fuzzy auto-acceptance. Multiple matching objects remain ambiguous.

Validate finite WGS84 coordinates against actual Census state polygons. A node contributes its published fuel point. A closed mapped fuel way contributes its first published vertex on the fuel facility, labeled `mapped_fuel_boundary`; this is not a calculated centroid or surveyed entrance. Relations and open/incomplete ways are rejected. The route planner retains its separate 200-metre road-snap and actual routed fuel-range checks.

Each station/extract/policy combination has a durable checkpoint and evidence in GeocodingCache. StationLocation links to the evidence, including source URL, OSM version/tags, matching factors, source station identity, extract checksum and date. Existing verified locations are preserved by this enrichment command. Resume skips completed checkpoints and moves to subsequent records; use --refresh to reevaluate rejected matches. Preserve the local extract for reproducibility. Source changes naturally produce a new checksum/checkpoint.

## Commands

From the repository root with the existing database configuration:

```powershell
./backend/.venv/Scripts/python.exe backend/manage.py enrich_osm_stations --file data/processed/tomah-osm.json --station-id 2
./backend/.venv/Scripts/python.exe backend/manage.py enrich_osm_stations --file data/processed/region-osm.json --state WI --limit 100 --dry-run
./backend/.venv/Scripts/python.exe backend/manage.py enrich_osm_stations --file data/processed/region-osm.json --state WI --limit 100
./backend/.venv/Scripts/python.exe backend/manage.py enrich_osm_stations --bbox 43.9 -90.6 44.1 -90.4 --state WI --limit 100
```

Offline input is a complete trusted OSM/Overpass JSON export with elements, tags and geometry. Do not supply invented or unlicensed input. Closed way geometry must contain the original ordered node coordinates; never insert a computed center. Dry-run creates/reuses an extract cache but does not update station locations or match checkpoints. The local diagnostic extract is ignored by Git; the live database retains it in GeocodingCache. This project does not yet convert regional PBF files to JSON. Obtain an OSM JSON export or supply such a converter for bulk work.

Prioritize I-90/I-94 through Wisconsin, then I-55/I-44 and I-10/I-40 with licensed regional extracts. Retain strict identity checks; the demonstrated Midwest corridor does not establish coverage on these other corridors.

## Live verification and Postman

[Actual response summary](station-enrichment-verification.json) records a fresh ORS Indianapolis-to-Minneapolis route: 595.205 miles, HTTP 200, 4,185 geometry points. A full 50-gallon tank requires a stop at route mile 426.240. Kwik Trip #796 (database ID 2, OPIS ID 9) purchases 9.520500278 gallons at the CSV median price $3.28733333/gallon, totaling $31.30. Initial fuel's historical cost is excluded. Arrival fuel 7.376 gallons; departure 16.897 gallons; second leg 168.965 miles; all range/tank constraints pass.

Coordinate: longitude -90.5028122, latitude 44.0189225, an existing vertex of [OSM way 1204194481](https://www.openstreetmap.org/way/1204194481), version 3, containing ref=796, brand=Kwik Trip, address=310 East McCoy Boulevard, city=Tomah, state=WI. Road snap: 5.13 metres. First request: two live ORS directions calls, zero geocoding calls, 5,337.60 ms end-to-end; cached repeat: zero external calls, 448.53 ms. Timings are observations, not guarantees.

Import the existing collection and select **Verified refueling: Indianapolis to Minneapolis**. Set base_url to http://127.0.0.1:8000 and start Django. Its four assertions require HTTP 200, a route over 500 miles with at least one stop, reconciled fuel/cost, valid tank/snap limits, and map geometry. Unlike the earlier coverage probes, it does not accept 422 as success.

With Django running, run the same request and test script from the command line:

```powershell
node docs/postman/verify-refueling.mjs http://127.0.0.1:8000
```

The minimal pm harness executed the collection's actual four assertions successfully over HTTP. It verifies this single request and does not emulate the full Postman runner; Postman desktop was not automated.
