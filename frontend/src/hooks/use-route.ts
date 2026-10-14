import {useState,useRef,useEffect} from 'react'
import {toast} from 'sonner'
import {ApiError,optimizeRoute,type OptimizeInput,type RouteResult} from '@/lib/api'
export function useRoute() {
 const [result,setResult]=useState<RouteResult|null>(null), [loading,setLoading]=useState(false), [error,setError]=useState<ApiError|null>(null)
 const controller=useRef<AbortController|null>(null)
 useEffect(()=>()=>controller.current?.abort(),[])
 async function submit(input:OptimizeInput) {
  controller.current?.abort(); const next=new AbortController();controller.current=next
  setLoading(true);setResult(null);setError(null)
  try { const route=await optimizeRoute(input,next.signal);if(!next.signal.aborted){setResult(route);toast.success('Your fuel plan is ready',{description:`${route.fuel_stops.length} verified fuel stop${route.fuel_stops.length===1?'':'s'} on your route.`})} }
  catch(e) { if(!next.signal.aborted){const issue=e instanceof ApiError?e:new ApiError('Something went wrong. Please retry.','unknown_error',0);setError(issue);toast.error('Route could not be planned',{description:issue.message})} }
  finally {if(!next.signal.aborted)setLoading(false)}
 }
 function reset(){controller.current?.abort();setLoading(false);setResult(null);setError(null)}
 return {result,loading,error,submit,reset}
}
