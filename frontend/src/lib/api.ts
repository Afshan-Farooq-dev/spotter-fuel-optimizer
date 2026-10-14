export type Location = string | { longitude: number; latitude: number }
export type OptimizeInput = { start: Location; destination: Location; initial_fuel_gallons: number; reserve_gallons: number }
export type FuelStop = { station_id: number; source_id: string; name: string; city: string; state: string; longitude: number; latitude: number; route_mile: string; price_per_gallon: string; gallons_purchased: string; cost: string; arrival_fuel_gallons: string; departure_fuel_gallons: string; road_snap_distance_metres: number }
export type RouteResult = { geometry: {type: 'LineString'; coordinates: [number,number][]}; distance_miles: string; duration_seconds: string; fuel_stops: FuelStop[]; total_cost: string; fuel_purchased_gallons: string; fuel_consumed_gallons: string; initial_fuel_gallons: string; remaining_fuel_gallons: string; reserve_gallons: string; vehicle: {maximum_range_miles:number;mpg:number;tank_gallons:number}; provider_usage: {directions_calls:number;directions_cache_hits:number}; verified_corridor_candidates:number; fuel_constraints_verified:boolean; optimization_scope:string; attribution:string }
export class ApiError extends Error { code: string; status: number; retryAfter: string | null; constructor(message:string, code:string, status:number, retryAfter:string|null=null) { super(message); this.code=code;this.status=status;this.retryAfter=retryAfter } }
function messages(value: unknown): string { if(typeof value==='string') return value; if(Array.isArray(value)) return value.map(messages).join(' '); if(value && typeof value==='object') return Object.entries(value).map(([key,v])=>`${key.replaceAll('_',' ')}: ${messages(v)}`).join(' '); return 'The request could not be completed.' }
export async function optimizeRoute(input: OptimizeInput, signal: AbortSignal): Promise<RouteResult> {
  let response:Response
  try { response=await fetch('/api/routes/optimize/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input),signal}) } catch(error) { if(signal.aborted) throw error; throw new ApiError('Cannot reach the route service. Check that Django is running and try again.','network_unavailable',0) }
  const payload=await response.json().catch(()=>null)
  if(!response.ok) throw new ApiError(payload?.error?.message || messages(payload),payload?.error?.code || (response.status===429 ? 'rate_limited':'invalid_request'),response.status,response.headers.get('Retry-After'))
  if(payload?.geometry?.type!=='LineString' || !Array.isArray(payload.geometry.coordinates) || payload.geometry.coordinates.length<2 || !Array.isArray(payload.fuel_stops)) throw new ApiError('The route service returned an incomplete response.','invalid_response',502)
  return payload
}
export const VERIFIED_TRIP = { start: {longitude:-86.1581,latitude:39.7684}, destination: {longitude:-93.265,latitude:44.9778} } as const
export const number = (value:string|number, digits=1) => Number(value).toLocaleString('en-US',{maximumFractionDigits:digits,minimumFractionDigits:digits})
export const money = (value:string|number) => Number(value).toLocaleString('en-US',{style:'currency',currency:'USD'})
