import {useEffect,useMemo,useRef,useState} from 'react'
import {MapContainer,TileLayer,Polyline,Marker,Popup,useMap} from 'react-leaflet'
import L from 'leaflet'
import {Expand,LocateFixed,Minus,Plus,Route} from 'lucide-react'
import {Button} from '@/components/ui/button'
import {money,number,type RouteResult} from '@/lib/api'
import 'leaflet/dist/leaflet.css'
const icon=(label:string,kind:string)=>L.divIcon({className:'route-pin',html:`<span class="pin-body ${kind}">${label}</span>`,iconSize:[32,32],iconAnchor:[16,16]})
function Viewport({result,selected}:{result:RouteResult|null;selected:number|null}){
 const map=useMap()
 useEffect(()=>{if(result)map.fitBounds(L.latLngBounds(result.geometry.coordinates.map(([lon,lat])=>[lat,lon])),{padding:[48,48],maxZoom:12,animate:false})},[map,result])
 useEffect(()=>{const stop=result?.fuel_stops.find(s=>s.station_id===selected);if(stop)map.setView([stop.latitude,stop.longitude],14,{animate:!window.matchMedia('(prefers-reduced-motion: reduce)').matches})},[selected,map,result])
 useEffect(()=>{const observer=new ResizeObserver(()=>map.invalidateSize());observer.observe(map.getContainer());return()=>observer.disconnect()},[map])
 return null
}
function Controls({result,onFullscreen}:{result:RouteResult|null;onFullscreen:()=>void}){
 const map=useMap()
 return <div className="map-controls"><Button variant="outline" size="icon" aria-label="Zoom in" onClick={()=>map.zoomIn()}><Plus size={17}/></Button><Button variant="outline" size="icon" aria-label="Zoom out" onClick={()=>map.zoomOut()}><Minus size={17}/></Button><Button variant="outline" size="icon" aria-label="Fit route to map" onClick={()=>{if(result)map.fitBounds(L.latLngBounds(result.geometry.coordinates.map(([lon,lat])=>[lat,lon])),{padding:[48,48]});else map.setView([39.5,-96],4)}}><LocateFixed size={17}/></Button><Button variant="outline" size="icon" aria-label="Toggle fullscreen map" onClick={onFullscreen}><Expand size={17}/></Button></div>
}
function StopMarker({stop,index,selected,onSelect}:{stop:RouteResult['fuel_stops'][number];index:number;selected:number|null;onSelect:(id:number)=>void}){
 const marker=useRef<L.Marker>(null)
 useEffect(()=>{if(selected===stop.station_id)marker.current?.openPopup()},[selected,stop.station_id])
 return <Marker ref={marker} position={[stop.latitude,stop.longitude]} icon={icon(String(index+1),'fuel')} eventHandlers={{click:()=>onSelect(stop.station_id)}}><Popup><div className="station-popup"><span>VERIFIED FUEL STOP {index+1}</span><strong>{stop.name}</strong><p>{stop.city}, {stop.state}</p><div>{number(stop.gallons_purchased,2)} gal · {money(stop.cost)}</div><small>CSV median {money(stop.price_per_gallon)}/gal</small></div></Popup></Marker>
}
export function RouteMap({result,selected,onSelect,loading}:{result:RouteResult|null;selected:number|null;onSelect:(id:number)=>void;loading:boolean}){
 const container=useRef<HTMLDivElement>(null)
 const [tileError,setTileError]=useState(false),[tileVersion,setTileVersion]=useState(0)
 const positions=useMemo(()=>result?.geometry.coordinates.map(([lon,lat])=>[lat,lon] as [number,number])??[],[result])
 const fullscreen=()=>{if(document.fullscreenElement)void document.exitFullscreen();else void container.current?.requestFullscreen().catch(()=>{})}
 return <section className="map-frame" ref={container} aria-label="Interactive driving route map"><div className="map-heading"><div><span className="map-live-dot"/> ROAD VIEW <span className="map-heading-detail">US driving routes</span></div><span><Route size={14}/> {result?'Route ready':'Plan your journey'}</span></div><div className="map-canvas">
 <MapContainer center={[39.5,-96]} zoom={4} zoomControl={false} scrollWheelZoom={false} className="leaflet-map"><TileLayer key={tileVersion} attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" eventHandlers={{tileerror:()=>setTileError(true)}}/><Viewport result={result} selected={selected}/><Controls result={result} onFullscreen={fullscreen}/>{positions.length>1&&<><Polyline positions={positions} pathOptions={{color:'#fff',weight:9,opacity:.9}}/><Polyline positions={positions} pathOptions={{color:'#237a53',weight:5,opacity:1}}/><Marker position={positions[0]} icon={icon('A','start')}><Popup>Starting point</Popup></Marker><Marker position={positions[positions.length-1]} icon={icon('B','finish')}><Popup>Destination</Popup></Marker></>}{result?.fuel_stops.map((stop,index)=><StopMarker key={stop.station_id} stop={stop} index={index} selected={selected} onSelect={onSelect}/>)}</MapContainer>
 {!result&&!loading&&<div className="map-empty"><div className="map-empty-icon"><Route size={24}/></div><strong>A clear road ahead.</strong><p>Plan a journey to see your route<br/>and verified fuel stops on the map.</p></div>}
 {loading&&<div className="map-loading" role="status"><span className="loading-line"/><strong>Finding your best fuel plan</strong><p>Checking the route and verified stations…</p></div>}
 {tileError&&<div className="tile-error" role="status">Map tiles couldn’t load. Route data remains available.<button onClick={()=>{setTileError(false);setTileVersion(v=>v+1)}}>Retry tiles</button></div>}
 <div className="map-legend"><span><i className="start-legend"/> Start</span><span><i className="fuel-legend"/> Fuel stop</span><span><i className="finish-legend"/> Destination</span></div></div></section>
}
