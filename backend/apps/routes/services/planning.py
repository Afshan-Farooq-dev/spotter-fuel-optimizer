"""Compose endpoint resolution, cached routing, spatial selection and fuel purchases."""
import math
from decimal import Decimal,ROUND_HALF_UP
from django.conf import settings
from apps.stations.models import FuelStation
from ..providers.http import ORSClient
from ..providers.directions import ORSDirections
from .domain import Candidate,PlanningError,TANK_GALLONS,miles_from_metres
from .locations import EndpointResolver
from .optimizer import optimize_fuel
from .candidates import route_candidates
from .routing import driving_route
from .audit import audit_fuel_plan

CENT=Decimal("0.01")


def snap_distance(first,second):
    lon1,lat1,lon2,lat2=map(math.radians,[*first,*second])
    a=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371008.8*2*math.asin(min(1,math.sqrt(a)))


def plan_route(data,*,provider=None,resolver=None):
    client=ORSClient(settings.ORS_API_KEY,timeout=settings.ROUTING_TIMEOUT,interval=settings.ORS_REQUEST_INTERVAL)
    provider=provider or ORSDirections(client);resolver=resolver or EndpointResolver(client)
    start=resolver.resolve(data["start"]);destination=resolver.resolve(data["destination"])
    origin=[start["longitude"],start["latitude"]];finish=[destination["longitude"],destination["latitude"]]
    if snap_distance(origin,finish)<1:raise PlanningError("Start and destination must be different locations.")
    initial=data.get("initial_fuel_gallons",TANK_GALLONS);reserve=data.get("reserve_gallons",Decimal(0))
    route=driving_route(provider,[origin,finish],ttl_seconds=settings.ROUTE_CACHE_SECONDS)
    candidates=[];selected=[];waypoint_stations=[];snap_offsets={}
    try:
        plan=optimize_fuel(route.miles,[],initial_gallons=initial,reserve_gallons=reserve)
    except PlanningError:
        candidates=route_candidates(route,corridor_metres=float(data.get("corridor_metres",settings.ROUTE_CORRIDOR_METRES)))
        try:
            # A selection reserve gives modest detour headroom; actual accounting uses the requested reserve.
            selection_reserve=max(reserve,min(reserve+Decimal(2),initial/2))
            try:provisional=optimize_fuel(route.miles,candidates,initial_gallons=initial,reserve_gallons=selection_reserve)
            except PlanningError:provisional=optimize_fuel(route.miles,candidates,initial_gallons=initial,reserve_gallons=reserve)
        except PlanningError as error:
            error.code="insufficient_station_coverage"
            error.details={"verified_corridor_candidates":len(candidates),"baseline_distance_miles":str(route.miles),
                           "directions_calls":provider.routing_calls,"directions_cache_hits":provider.cache_hits}
            raise
        lookup={s.station_id:s for s in candidates}
        selected=[lookup[p.station_id] for p in provisional.purchases]
        if any(s.longitude is None or s.latitude is None for s in selected):
            error=PlanningError("Selected fuel station has no verified coordinate.")
            error.code="missing_station_coordinates";raise error
        if len(selected)>48:raise PlanningError("Fuel plan exceeds ORS's 50-waypoint request limit.")
        coordinates=[origin]+[[s.longitude,s.latitude] for s in selected]+[finish]
        route=driving_route(provider,coordinates,ttl_seconds=settings.ROUTE_CACHE_SECONDS)
        cumulative=Decimal(0);verified=[]
        for index,station in enumerate(selected):
            cumulative+=miles_from_metres(route.leg_metres[index])
            snapped=route.geometry["coordinates"][route.waypoint_indices[index+1]]
            offset=snap_distance([station.longitude,station.latitude],snapped)
            if offset>settings.STATION_MAX_SNAP_METRES:
                error=PlanningError("ORS snapped a fuel stop too far from its verified station point.")
                error.code="station_access_not_verified";raise error
            snap_offsets[station.station_id]=offset
            verified.append(Candidate(station.station_id,cumulative,station.price,station.longitude,station.latitude))
        try:plan=optimize_fuel(route.miles,verified,initial_gallons=initial,reserve_gallons=reserve)
        except PlanningError as error:
            error.code="verified_route_infeasible";raise
        waypoint_stations=[s.station_id for s in selected]
    audit_fuel_plan(plan,reserve)
    stations=FuelStation.objects.in_bulk([p.station_id for p in plan.purchases])
    stops=[];total=Decimal(0)
    for purchase in plan.purchases:
        station=stations[purchase.station_id]
        cost=purchase.cost.quantize(CENT,rounding=ROUND_HALF_UP);total+=cost
        candidate=next(s for s in selected if s.station_id==purchase.station_id)
        stops.append({"station_id":station.pk,"source_id":station.source_id,"name":station.name,
            "city":station.city,"state":station.state,"longitude":candidate.longitude,"latitude":candidate.latitude,
            "route_mile":str(purchase.miles),"price_per_gallon":str(purchase.price),
            "gallons_purchased":str(purchase.gallons),"cost":str(cost),
            "arrival_fuel_gallons":str(purchase.arrival_gallons),"departure_fuel_gallons":str(purchase.departure_gallons),
            "road_snap_distance_metres":round(snap_offsets.get(station.pk,0),2)})
    return {"start":start,"destination":destination,"geometry":route.geometry,
        "distance_metres":str(route.distance_metres),"distance_miles":str(route.miles),
        "duration_seconds":str(route.duration_seconds),"fuel_stops":stops,"total_cost":str(total.quantize(CENT)),
        "currency":"USD","fuel_consumed_gallons":str(plan.consumed_gallons),
        "fuel_purchased_gallons":str(plan.purchased_gallons),"initial_fuel_gallons":str(plan.initial_gallons),
        "remaining_fuel_gallons":str(plan.remaining_gallons),"reserve_gallons":str(reserve),
        "vehicle":{"maximum_range_miles":500,"mpg":10,"tank_gallons":50},
        "route_waypoint_station_ids":waypoint_stations,
        "optimization_scope":"minimum fuel purchases for the selected verified driving sequence",
        "cost_basis":"new purchases; historical cost of initial fuel excluded",
        "attribution":"openrouteservice by HeiGIT; OpenStreetMap contributors",
        "provider_usage":{"directions_calls":provider.routing_calls,"directions_cache_hits":provider.cache_hits,
            "geocoding_calls":resolver.geocoding_calls,"geocoding_cache_hits":resolver.cache_hits},
        "verified_corridor_candidates":len(candidates),"fuel_constraints_verified":True}
