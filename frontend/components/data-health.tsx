'use client';
import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {AlertTriangle,CheckCircle2,Loader2,PlugZap} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

export type Backfill={locations:number;percent:number;complete:boolean;synced_through:string|null};
export type Health={environment:string;connected:boolean;status:'not_connected'|'needs_reconnect'|'revoked'|'importing'|'error'|'stale'|'healthy';
  message:string;last_success_at:string|null;backfill:Backfill|null;job:{status:string;attempts:number;last_error:string|null}|null;gaps:string[]};

/** Loads data health and keeps polling while history is importing. */
export function useDataHealth(){
 const [health,setHealth]=useState<Health|null>(null);
 const load=useCallback(async()=>{
  try{const s=await localAuthClient().auth.getSession();const t=s.data.session?.access_token;
   if(!t){setHealth(null);return}
   setHealth(await accountApi('/api/integrations/square/health',t) as Health);
  }catch{/* banner is advisory; pages show their own errors */}
 },[]);
 useEffect(()=>{void load()},[load]);
 useEffect(()=>{
  if(health?.status!=='importing')return;
  const id=setInterval(()=>void load(),4000);return()=>clearInterval(id);
 },[health?.status,load]);
 return {health,reload:load};
}

/** Shown above account pages whenever the numbers shouldn't be fully trusted yet. */
export function DataHealthBanner({health}:{health:Health|null}){
 if(!health||!health.connected||health.status==='healthy')return null;
 const reconnect=health.status==='needs_reconnect'||health.status==='revoked';
 const importing=health.status==='importing';
 return <div className={'ts9-notice '+(reconnect||health.status==='error'?'danger':'')} role="status" data-health={health.status}>
  {importing?<Loader2 size={17}/>:reconnect?<PlugZap size={17}/>:<AlertTriangle size={17}/>}
  <span>{health.message} {health.status==='stale'||health.status==='error'||health.status==='importing'?'Trend conclusions are paused until Square data is complete and current.':''}</span>
  {importing&&health.backfill&&<progress max={100} value={health.backfill.percent} aria-label="History import progress" style={{marginLeft:8}}/>}
  {reconnect&&<Link href="/connections" style={{fontWeight:700,marginLeft:8}}>Reconnect Square</Link>}
  {(health.status==='stale'||health.status==='error')&&<Link href="/connections" style={{fontWeight:700,marginLeft:8}}>Sync now</Link>}
 </div>;
}

export function HealthSummary({health}:{health:Health|null}){
 if(!health||!health.connected)return null;
 return <div className="ts9-connection-meta" aria-label="Data health">
  <div><small>Data status</small><strong>{health.status==='healthy'?<><CheckCircle2 size={14}/> Up to date</>:health.message}</strong></div>
  <div><small>History imported</small><strong>{health.backfill?`${health.backfill.percent}%`:'—'}</strong></div>
  <div><small>Last update</small><strong>{health.last_success_at?new Date(health.last_success_at).toLocaleString():'Not yet'}</strong></div>
  {health.gaps.length>0&&<div style={{gridColumn:'1 / -1'}}><small>What these numbers don't include</small><ul style={{margin:'4px 0 0',paddingLeft:18}}>{health.gaps.map(g=><li key={g}>{g}</li>)}</ul></div>}
 </div>;
}
