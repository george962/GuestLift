'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity, ArrowDown, ArrowDownRight, ArrowLeftRight, ArrowRight, ArrowUpRight, BarChart3, Check, CheckCircle2,
  ChevronDown, ChevronRight, CircleCheck, Clock3, Code2, Copy, Database, FileJson2, FileSpreadsheet, Filter,
  GitMerge, Info, LoaderCircle, LockKeyhole, Play, RotateCcw, Search, Server, ShieldAlert, ShieldCheck, Sparkles, Table2, Workflow, X
} from 'lucide-react';
import localData from '@/lib/demo-fallback.json';
import type { Metrics, Order, Preview, Provider } from '@/lib/types';
import {calculateMetrics, fmtInt, usd} from '@/lib/types';

const api = process.env.NEXT_PUBLIC_GUESTLIFT_API_URL || 'http://localhost:8000';
const sources:Record<Provider,{name:string,format:string,short:string,icon:string,theme:string}>={
 toast:{name:'Toast POS',format:'CSV · Order / Item / Payment',short:'t',icon:'t',theme:'toast'},
 square:{name:'Square POS',format:'JSON · Orders + Payments',short:'■',icon:'■',theme:'square'}
};
const stages=[{title:'Source',subtitle:'Vendor records',icon:FileSpreadsheet},{title:'Adapter',subtitle:'Parse & map',icon:GitMerge},{title:'GRDC',subtitle:'Validate contract',icon:ShieldCheck},{title:'Database',subtitle:'Store records',icon:Database},{title:'Analytics',subtitle:'Shared metrics',icon:BarChart3}];
function getLocal(provider:Provider):Preview{return localData[provider] as Preview}
function timeLabel(v:string){try{const date=new Date(v);return isNaN(+date)?v:date.toLocaleDateString('en-US',{month:'short',day:'numeric'})}catch{return v}}

export default function Demo(){
 const [provider,setProvider]=useState<Provider>('toast');
 const [backend,setBackend]=useState(false);
 const [loading,setLoading]=useState(false);
 const [activeStep,setActiveStep]=useState(-1);
 const [loaded,setLoaded]=useState<Provider[]>([]);
 const [metrics,setMetrics]=useState<Metrics|null>(null);
 const [selected,setSelected]=useState<Order|null>(null);
 const [view,setView]=useState<'canonical'|'source'>('canonical');
 const [panel,setPanel]=useState<'overview'|'records'>('overview');
 const [message,setMessage]=useState('');
 const [error,setError]=useState('');
 const [bootChecked,setBootChecked]=useState(false);
 const preview=getLocal(provider);

 useEffect(()=>{let cancelled=false;fetch(`${api}/api/health`,{signal:AbortSignal.timeout(2500)}).then(r=>r.ok?r.json():Promise.reject()).then(()=>{if(!cancelled)setBackend(true)}).catch(()=>{if(!cancelled)setBackend(false)}).finally(()=>{if(!cancelled)setBootChecked(true)});return()=>{cancelled=true}},[]);

 // Keep the initial page useful even when the local API has not been started.
 const run=useCallback(async()=>{
  setLoading(true);setError('');setMessage('');setSelected(null);
  for(let i=0;i<stages.length;i++){setActiveStep(i);await new Promise(resolve=>setTimeout(resolve,245))}
  try{
   if(backend){
    const resp=await fetch(`${api}/api/import/${provider}`,{method:'POST'});
    if(!resp.ok)throw new Error((await resp.json()).detail||'Import failed');
    const info=await resp.json();
    const measured=await fetch(`${api}/api/metrics`).then(r=>r.json());
    setMetrics(measured);
    setMessage(info.inserted ? `${info.inserted} new canonical orders stored. ${info.duplicates} previously imported.` : `Replay detected. ${info.duplicates} orders already stored; no duplicate sales created.`);
   }else{
    const providers=Array.from(new Set([...loaded,provider]));
    const combined=providers.flatMap(p=>getLocal(p).records);
    setMetrics(calculateMetrics(combined));
    setMessage(`${preview.records.length} pre-normalized sample orders loaded for browser preview. Start the Python API to run the actual adapters and persistence.`);
   }
   setLoaded(prev=>Array.from(new Set([...prev,provider])));
   setPanel('overview');
  }catch(e){setError(e instanceof Error?e.message:'Pipeline error')}
  finally{setLoading(false)}
 },[backend,provider,preview.records.length,loaded]);
 const reset=async()=>{
  setError('');setMessage('');setMetrics(null);setActiveStep(-1);setSelected(null);setLoaded([]);
  if(backend){try{await fetch(`${api}/api/reset`,{method:'POST'})}catch{setBackend(false)}}
 };
 const currentMetrics=metrics;
 const visibleOrders=(currentMetrics?.orders||[]).filter(o=>o.provider===provider);
 const maxLocation=Math.max(1,...(metrics?.locations||[]).map(l=>l.net_sales_minor));
 const rawView=preview.raw_snippet||(preview.files?.[provider==='toast'?'OrderDetails.csv':'orders.json']?.slice(0,3700))||'';
 const sample=selected||preview.records[0];
 const currentSource=sources[provider];
 return <main className="demo-app"><div className="demo-topbar"><div className="site-width demo-topbar-inner"><span className="demo-navline"><span className="demo-status-dot"/> INTERACTIVE PRODUCT PREVIEW</span><span className="demo-topbar-note"><LockKeyhole size={13}/> Only fictional / synthetic records</span></div></div>
 <div className="site-width demo-intro"><div><span className="eyebrow">PIPELINE STUDIO / BETA</span><h1>See the data <em>come together.</em></h1><p>Choose a source, run a sample pipeline, and explore exactly how GuestLift standardizes restaurant information.</p></div><div className="connection-pill"><span className={backend?'green-pulse':'amber-pulse'}/><div><b>{backend?'Local API connected':'Browser preview mode'}</b><small>{backend?'Python adapters + SQL persistence':'Start FastAPI for real imports'}</small></div></div></div>
 <div className="site-width demo-layout">
 <aside className="demo-aside"><div className="aside-header"><span>WORKSPACE</span><span>01</span></div><button className={'aside-item '+(panel==='overview'?'aside-active':'')} onClick={()=>setPanel('overview')}><Workflow size={17}/> Pipeline overview</button><button className={'aside-item '+(panel==='records'?'aside-active':'')} onClick={()=>setPanel('records')}><Table2 size={17}/> Canonical records</button><div className="aside-divider"/><span className="aside-label">AVAILABLE SOURCES</span><button className={'aside-source '+(provider==='toast'?'source-active':'')} onClick={()=>{setProvider('toast');setSelected(null)}}><span className="aside-source-icon toast-color">t</span><div><b>Toast POS</b><small>CSV sample</small></div>{provider==='toast'&&<Check size={16}/>}</button><button className={'aside-source '+(provider==='square'?'source-active':'')} onClick={()=>{setProvider('square');setSelected(null)}}><span className="aside-source-icon square-color">■</span><div><b>Square POS</b><small>JSON sample</small></div>{provider==='square'&&<Check size={16}/>}</button><div className="aside-explainer"><Sparkles size={18}/><b>Built for transparency</b><p>Every number can be traced to source records. Nothing here comes from a live restaurant.</p><Link href="/how-it-works">Our methodology <ArrowUpRight size={14}/></Link></div></aside>
 <section className="demo-main"><div className="demo-panel-head"><div><span className="panel-kicker">DATA SOURCE</span><h2>Start with a POS provider</h2></div><button onClick={reset} className="ghost-button"><RotateCcw size={14}/> Reset</button></div>
 <div className="source-selector"><button className={'source-choice '+(provider==='toast'?'chosen':'')} onClick={()=>{setProvider('toast');setSelected(null)}}><span className="source-choice-icon toast-color">t</span><span><b>Toast POS</b><small>Order, item & payment CSV</small></span>{provider==='toast'?<CircleCheck size={20}/>:<span className="select-circle"/>}</button><button className={'source-choice '+(provider==='square'?'chosen':'')} onClick={()=>{setProvider('square');setSelected(null)}}><span className="source-choice-icon square-color">■</span><span><b>Square POS</b><small>Orders + payment JSON</small></span>{provider==='square'?<CircleCheck size={20}/>:<span className="select-circle"/>}</button></div>
 <div className="pipeline-panel"><div className="pipeline-panel-heading"><div><span className="panel-kicker">01 / INGESTION PIPELINE</span><h3>{currentSource.name} → GuestLift</h3></div><span className="fixture-label"><span/> Sample data</span></div>
 <div className="demo-pipeline">{stages.map((s,i)=>{const Icon=s.icon;const active=activeStep>=i;return <div className="demo-pipeline-unit" key={s.title}><div className={'demo-pipeline-node '+(active?'node-done':'')+(activeStep===i&&loading?' node-running':'')}><div className="node-icon"><Icon size={19}/></div><span><b>{s.title}</b><small>{s.subtitle}</small></span>{active&&!loading?<CheckCircle2 size={15} className="node-check"/>:null}</div>{i<stages.length-1&&<div className={'demo-pipeline-connector '+(activeStep>i?'connector-done':'')}><ArrowRight size={17}/></div>}</div>})}</div>
 <div className="pipeline-actions"><span><Info size={15}/> {provider==='toast'?'Three small, fabricated CSV reports':'API-shaped JSON fixture, not live Square Sandbox'} · {fmtInt(preview.records.length)} orders</span><button className="btn btn-dark btn-small" onClick={run} disabled={loading}>{loading?<><LoaderCircle className="spin" size={17}/> Running…</>:<><Play size={16} fill="currentColor"/> {loaded.includes(provider)?'Replay sample':'Run sample pipeline'}</>}</button></div>
 {message&&<div className="success-message"><CheckCircle2 size={18}/>{message}</div>}{error&&<div className="error-message"><ShieldAlert size={18}/>{error}</div>}</div>
 {panel==='overview'?<>
 <div className="metrics-heading"><div><span className="panel-kicker">02 / RECONCILED ANALYTICS</span><h3>Business overview</h3></div><span className="small-muted">{metrics?'Computed from imported demo records':'Run the pipeline to see results'}</span></div>
 <div className="demo-metrics-grid"><div className="demo-metric"><div><span>Net sales</span><BarChart3 size={17}/></div><strong>{metrics?usd(metrics.net_sales_minor):'—'}</strong><small>Pretax · minus discounts & refunds</small></div><div className="demo-metric"><div><span>Orders imported</span><FileSpreadsheet size={17}/></div><strong>{metrics?fmtInt(metrics.order_count):'—'}</strong><small>Unique source orders</small></div><div className="demo-metric"><div><span>Total discounts</span><ArrowDownRight size={17}/></div><strong>{metrics?usd(metrics.discounts_minor):'—'}</strong><small>Deducted once from item gross</small></div><div className="demo-metric"><div><span>Sales refunds</span><ArrowLeftRight size={17}/></div><strong>{metrics?usd(metrics.refunds_minor):'—'}</strong><small>Demo pretax refund amounts</small></div></div>
 <div className="viz-row"><div className="viz-card"><div className="viz-title"><div><span className="panel-kicker">LOCATION PERFORMANCE</span><h3>Net sales by location</h3></div><span className="viz-key"><span/> Demo orders</span></div><div className="location-bars">{metrics?.locations?.length?metrics.locations.map((l,i)=><div className="location-bar-row" key={l.location_id}><span title={l.location_id}>{l.location_id.replace('Northline · ','').replace('sq-','').replace(/^[a-z]/,c=>c.toUpperCase())}</span><div className="bar-track"><div className={'bar-fill bar-'+(l.provider==='toast'?'toast':'square')} style={{width:Math.max(3,100*l.net_sales_minor/maxLocation)+'%'}}/></div><b>{usd(l.net_sales_minor)}</b></div>):<div className="empty-viz"><BarChart3 size={26}/><p>Import a sample to generate the location chart</p></div>}</div></div>
 <div className="viz-card quality-card"><div className="viz-title"><div><span className="panel-kicker">DATA TRUST</span><h3>Ingestion checks</h3></div><ShieldCheck size={19}/></div><div className="quality-score"><span>{metrics?'100%':'—'}</span><small>fixture parse success</small></div><div className="quality-lines"><div><CheckCircle2 size={16}/><span>Canonical contract</span><b>{metrics?'Valid':'Pending'}</b></div><div><CheckCircle2 size={16}/><span>Duplicate handling</span><b>{metrics?'Enabled':'Pending'}</b></div><div><Info size={16}/><span>Merchant data</span><b>None</b></div></div><p className="quality-fineprint">Quality score reflects bundled sample fixture validation, not completeness or certification of real merchant exports.</p></div></div>
 </>:<div className="records-panel"><div className="metrics-heading"><div><span className="panel-kicker">02 / SOURCE LINEAGE</span><h3>Canonical orders</h3></div><span className="small-muted">Click a record to inspect its components</span></div><OrderTable records={visibleOrders} onChoose={setSelected} selectedId={selected?.source_order_id}/></div>}
 <div className="records-preview"><div className="records-heading"><div><span className="panel-kicker">03 / AUDIT TRAIL</span><h3>Look inside a record</h3></div><div className="code-toggle"><button onClick={()=>setView('source')} className={view==='source'?'selected':''}>Source</button><button onClick={()=>setView('canonical')} className={view==='canonical'?'selected':''}>GRDC</button></div></div><div className="code-description">{view==='source'?<>An excerpt from the bundled <b>{currentSource.name}</b> example file. It contains no customer-owned data.</>:<>The shared GuestLift representation of order <b>{sample.source_order_id}</b>. You can inspect items, payments and source lineage.</>}</div><pre className="code-window"><code>{view==='source'?rawView:JSON.stringify(sample,null,2)}</code></pre><div className="records-footer"><span><Code2 size={16}/> {view==='source'?(preview.raw_file||'example source'):'GRDC draft v0.1'} · synthetic fixture</span><button onClick={()=>{if(typeof navigator!=='undefined')navigator.clipboard?.writeText(view==='source'?rawView:JSON.stringify(sample,null,2))}}><Copy size={15}/> Copy</button></div></div>
 <div className="demo-disclaimer"><ShieldAlert size={22}/><div><b>About this demonstration</b><p>{backend?'The local Python API is parsing fabricated vendor-shaped files and persisting their standardized records.':'This is a standalone browser preview using bundled, pre-normalized fixture data. To run the actual Python importers and database, follow the README quickstart.'} These are fictional transactions. The prototype is not connected to Toast, Square, real merchants, or production accounts.</p></div></div>
 </section></div>
 </main>
}
function OrderTable({records,onChoose,selectedId}:{records:Order[],onChoose:(o:Order)=>void,selectedId?:string}){
return <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Order ID</th><th>Location</th><th>Items</th><th>Net sales</th><th>Status</th><th></th></tr></thead><tbody>{records.length?records.slice(0,15).map(o=><tr key={o.source_order_id} className={o.source_order_id===selectedId?'selected-order':''} onClick={()=>onChoose(o)}><td><b>{o.source_order_id}</b></td><td>{o.location_id.replace('Northline · ','')}</td><td>{o.items.length}</td><td>{usd(o.net_sales_minor)}</td><td><span className="table-status">{o.status}</span></td><td><ChevronRight size={16}/></td></tr>):<tr><td colSpan={6}><div className="orders-empty">Run an import to see canonical orders here.</div></td></tr>}</tbody></table></div>
}
