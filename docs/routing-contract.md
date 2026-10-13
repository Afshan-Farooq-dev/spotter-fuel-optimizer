# Routing phase contract

POST /api/routes/optimize/ accepts start and destination as US place text or
WGS84 longitude/latitude objects. Vehicle constants: 500 miles maximum range,
10 miles per US gallon, 50-gallon capacity.

Initial fuel defaults to 50 gallons. It can be supplied explicitly. Purchase
expenditure excludes the historical cost of initial fuel; a full-tank trip under
500 miles can therefore have no stops and zero new purchases. Fuel consumed is
reported separately. Optional reserve is retained throughout the trip.

An indexed PostGIS corridor query finds verified stations along a baseline ORS
driving route. Baseline station ordering/chainage is an estimate used for stop
selection. Final directions through chosen fuel stops supply actual leg distances
and map geometry. The plan is rejected if those verified legs violate fuel
reachability; estimated detours are never returned as verified driving geometry.

One directions call is used for trips with no refueling, normally two when stops
need road verification. Directions and endpoint geocoding are cached independently
of prices. Price changes are read on each request.

The greedy algorithm minimizes purchases for a fixed ordered station sequence
with continuous fuel quantities. It does not claim to find the globally cheapest
road path or all possible off-route station detours. If final detours invalidate
the selected sequence, the response reports infeasibility instead of exceeding
500 miles or fabricating access distances.

No coordinates, fuel prices, route distances or computed costs are hardcoded into
application results. Synthetic routing/geocoding fixtures are used only in tests.
