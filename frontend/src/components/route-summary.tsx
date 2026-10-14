import {Coins,Fuel,MapPinned,Milestone} from 'lucide-react'
import {Card} from '@/components/ui/card'
import {number,money,type RouteResult} from '@/lib/api'
export function RouteSummary({result,loading}:{result:RouteResult|null;loading:boolean}){
 const stats=[{label:'TOTAL DISTANCE',value:result?number(result.distance_miles):'—',unit:'mi',icon:Milestone,note:result?'Actual driving distance':'Your journey, measured'}, {label:'FUEL STOPS',value:result?String(result.fuel_stops.length):'—',unit:'stops',icon:MapPinned,note:result?'Verified station locations':'Verified along your route'}, {label:'FUEL TO PURCHASE',value:result?number(result.fuel_purchased_gallons,2):'—',unit:'gal',icon:Fuel,note:result?'Starting fuel excluded':'Only the fuel you need'}, {label:'TOTAL FUEL COST',value:result?money(result.total_cost):'—',unit:result?'USD':'',icon:Coins,note:result?'Based on CSV median prices':'Calculated from supplied prices'}]
 return <section className="summary-grid" aria-label="Route summary" aria-busy={loading}>{stats.map(({label,value,unit,icon:Icon,note},index)=><Card key={label} className={`stat-card ${index===3?'cost-card':''}`}><div className="stat-top"><span>{label}</span><Icon size={17}/></div><div className={`stat-value ${loading?'skeleton-text':''}`}>{loading?'':value}<span>{!loading&&unit}</span></div><p>{note}</p></Card>)}</section>
}
