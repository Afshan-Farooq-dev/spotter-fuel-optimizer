import {ArrowDownUp,ArrowUpRight,Check,ChevronDown,Fuel,LoaderCircle,MapPin,Navigation,Route,ShieldCheck,Sparkles} from 'lucide-react'
import {Button} from '@/components/ui/button'
import {Input} from '@/components/ui/input'
export type TripForm = {start:string;destination:string;initial:number;reserve:number;verified:boolean}
type Props={form:TripForm;onEdit:(patch:Partial<TripForm>)=>void;onSubmit:()=>void;onExample:()=>void;loading:boolean}
export function RoutePlanner({form,onEdit,onSubmit,onExample,loading}:Props){
return <section className="planner" aria-labelledby="planner-title">
 <div className="eyebrow"><span className="tiny-square"/> ROUTE WORKSPACE</div><h2 id="planner-title">Every mile.<br/><span>A smarter plan.</span></h2><p className="intro">Find verified fuel stops and make your next journey more cost effective.</p>
 <form onSubmit={e=>{e.preventDefault();onSubmit()}}>
 <div className="location-fields"><div className="journey-line"/><label className="field-label" htmlFor="origin"><Navigation size={15}/> STARTING POINT</label><Input id="origin" autoComplete="off" list="cities" maxLength={250} required minLength={2} value={form.start} onChange={e=>onEdit({start:e.target.value})} placeholder="US place or latitude, longitude" className="location-input"/>
 <Button type="button" variant="ghost" size="icon" className="swap" aria-label="Swap start and destination" disabled={loading} onClick={()=>onEdit({start:form.destination,destination:form.start})}><ArrowDownUp size={16}/></Button>
 <label className="field-label destination-label" htmlFor="destination"><MapPin size={15}/> DESTINATION</label><Input id="destination" autoComplete="off" list="cities" maxLength={250} required minLength={2} value={form.destination} onChange={e=>onEdit({destination:e.target.value})} placeholder="Where are you headed?" className="location-input"/>
 <datalist id="cities"><option value="Indianapolis, IN"/><option value="Minneapolis, MN"/><option value="Chicago, IL"/><option value="Houston, TX"/><option value="Dallas, TX"/></datalist></div>
 <details className="vehicle"><summary><div className="vehicle-icon"><Fuel size={18}/></div><div><strong>Standard vehicle</strong><span>50 gal tank · 10 MPG · 500 mi range</span></div><ChevronDown size={15}/></summary><div className="fuel-inputs"><label htmlFor="initial">Starting fuel (gal)<Input id="initial" type="number" min={0} max={50} step="0.001" required value={form.initial} onChange={e=>onEdit({initial:e.target.valueAsNumber})}/></label><label htmlFor="reserve">Arrival reserve (gal)<Input id="reserve" type="number" min={0} max={Number.isFinite(form.initial)?Math.min(form.initial,49.999):49.999} step="0.001" required value={form.reserve} onChange={e=>onEdit({reserve:e.target.valueAsNumber})}/></label></div></details>
 <Button type="submit" className="optimize-button" disabled={loading}>{loading?<LoaderCircle size={17} className="animate-spin"/>:<Route size={17}/>} {loading?'Planning your route…':'Optimize route'} {!loading&&<ArrowUpRight size={17}/>}</Button>
 </form>
 <div className="form-note"><ShieldCheck size={14}/><span>US routes. Genuine station coordinates.</span></div>
 <div className="example-card"><div className="example-heading"><Sparkles size={15}/><span>TAKE IT FOR A SPIN</span></div><strong>A journey we’ve verified.</strong><p>Indianapolis <span>→</span> Minneapolis</p><Button type="button" variant="outline" onClick={onExample} disabled={loading}>Load verified route <ArrowUpRight size={14}/></Button><div className="verified-note"><Check size={12}/> Live directions. Real fuel prices.</div></div>
 <div className="coverage-note"><div className="coverage-dot"/><div><strong>Coverage is growing</strong><p>Only sufficiently verified stations are eligible. Some long routes may not have enough fuel stops yet.</p></div></div>
 <footer className="planner-footer"><span>POWERED BY REAL ROAD DATA</span><span>openrouteservice + OpenStreetMap</span></footer>
</section>
}
