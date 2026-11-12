'use client';

import {useEffect,useMemo,useRef,useState} from 'react';
import Link from 'next/link';
import {
  ArrowRight,ArrowUpRight,BarChart3,Check,CheckCircle2,ChevronDown,ClipboardCheck,Code2,Database,
  Download,FileJson2,FileSpreadsheet,FileUp,GitMerge,Info,LockKeyhole,Play,Receipt,
  RotateCcw,Search,ShieldAlert,ShieldCheck,Table2,TicketPercent,UploadCloud,X
} from 'lucide-react';
import type {Order,Provider} from '@/lib/types';
import {calculateMetrics,usd} from '@/lib/types';
import {DEMO_FILES,transformUploaded,parseCsv} from '@/lib/browser-import.mjs';

type Parsed={provider:Provider;records:Order[];warnings:string[];summary:{orders:number;items:number;payments:number;net_sales_minor:number;discounts_minor:number;refunds_minor:number}};
const names:{id:Provider;name:string;format:string;desc:string}[]=[
  {id:'toast',name:'Toast POS',format:'Three CSV reports',desc:'OrderDetails, ItemSelectionDetails and PaymentDetails'},
  {id:'square',name:'Square POS',format:'Three JSON fixtures',desc:'Orders, payments and refunds (API-shaped examples)'},
];
const api = process.env.NEXT_PUBLIC_GUESTLIFT_API_URL || 'http://localhost:8000';
const stages=[{name:'Source files',detail:'Read uploaded text',icon:FileSpreadsheet},{name:'Adapter',detail:'Resolve provider fields',icon:GitMerge},{name:'GRDC',detail:'Validate unified records',icon:ShieldCheck},{name:'Storage',detail:'Browser or local SQL',icon:Database},{name:'Reporting',detail:'Compute metrics',icon:BarChart3}];
function shortJson(record:Order){return JSON.stringify({provider:record.provider,source_order_id:record.source_order_id,location_id:record.location_id,gross_minor:record.gross_minor,discount_minor:record.discount_minor,refund_minor:record.refund_minor,net_sales_minor:record.net_sales_minor,items:record.items,payments:record.payments,warnings:record.warnings},null,2)}

export default function ImportLab(){
  const [provider,setProvider]=useState<Provider>('toast');
  const [selectedFiles,setSelectedFiles]=useState<File[]>([]);
  const [sampleTexts,setSampleTexts]=useState<Record<string,string>|null>(null);
  const [lastContents,setLastContents]=useState<Record<string,string>|null>(null);
  const [result,setResult]=useState<Parsed|null>(null);
  const [allOrders,setAllOrders]=useState<Order[]>([]);
  const [selectedOrder,setSelectedOrder]=useState<string>('');
  const [apiAvailable,setApiAvailable]=useState(false);
  const [lastApi,setLastApi]=useState<{inserted:number;duplicates:number;import_id:string}|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [status,setStatus]=useState('');
  const [filter,setFilter]=useState('');
  const [activeStage,setActiveStage]=useState(-1);
  const [inspectTab,setInspectTab]=useState<'source'|'grdc'>('grdc');
  const fileInput=useRef<HTMLInputElement>(null);

  useEffect(()=>{
    if(!['localhost','127.0.0.1'].includes(window.location.hostname))return;
    fetch(`${api}/api/health`,{signal:AbortSignal.timeout(2000)}).then(r=>setApiAvailable(r.ok)).catch(()=>setApiAvailable(false));
  },[]);

  const required=DEMO_FILES[provider];
  const chosen=selectedFiles.length>0?Object.fromEntries(selectedFiles.map(f=>[f.name,'Selected'])):sampleTexts;
  const displayed=useMemo(()=>{
    const source=result?.records??[];
    return source.filter(o=>`${o.source_order_id} ${o.location_id} ${o.items.map(i=>i.name).join(' ')}`.toLowerCase().includes(filter.toLowerCase()));
  },[result,filter]);
  const inspected=result?.records.find(o=>o.source_order_id===selectedOrder)??result?.records[0];
  const totals=useMemo(()=>calculateMetrics(result?.records??[]),[result]);
  const maxLocation=Math.max(1,...totals.locations.map(l=>l.net_sales_minor));

  function changeProvider(next:Provider){setProvider(next);setSelectedFiles([]);setSampleTexts(null);setLastContents(null);setResult(null);setSelectedOrder('');setError('');setStatus('');setActiveStage(-1);setLastApi(null);if(fileInput.current)fileInput.current.value='';}
  function uploadChosen(files:FileList|null){
    if(!files)return;
    setSelectedFiles(Array.from(files));setSampleTexts(null);setLastContents(null);setResult(null);setError('');setStatus('');setActiveStage(-1);setLastApi(null);
  }
  async function loadDemo(){
    setBusy(true);setError('');setStatus('');setResult(null);setSelectedFiles([]);
    if(fileInput.current)fileInput.current.value='';
    try{
      const entries=await Promise.all(required.map(async name=>{
        const response=await fetch(`/samples/${provider}/${name}`);
        if(!response.ok)throw new Error(`Could not fetch ${name}; is the website serving its sample files?`);
        return [name,await response.text()] as const;
      }));
      setSampleTexts(Object.fromEntries(entries));setStatus('Synthetic sample files loaded. Click Run import to process them.');
    }catch(e){setError(e instanceof Error?e.message:'Unable to load samples')}
    finally{setBusy(false)}
  }
  async function run(){
    setBusy(true);setError('');setStatus('');setLastApi(null);setResult(null);setActiveStage(0);
    try{
      let contents:Record<string,string>;
      if(selectedFiles.length){
        const names=selectedFiles.map(f=>f.name);
        if(names.length!==required.length||required.some(n=>!names.includes(n))||new Set(names).size!==names.length)throw new Error(`Upload exactly: ${required.join(', ')}`);
        if(selectedFiles.some(f=>f.size>2*1024*1024||f.size===0))throw new Error('Each file must be non-empty and smaller than 2 MB. Demo-only limit.');
        contents=Object.fromEntries(await Promise.all(selectedFiles.map(async f=>[f.name,await f.text()])));
      }else if(sampleTexts){contents=sampleTexts;}
      else throw new Error('First upload the required files or select Load synthetic sample.');
      setActiveStage(1);
      const transformed=transformUploaded(provider,contents) as Parsed;
      setActiveStage(2);
      // Preserve only canonical, fictional output in session memory for the Offer Studio link.
      // This is never sent to a hosted backend on the public static site.
      const next=[...allOrders.filter(x=>!transformed.records.some(o=>o.provider===x.provider&&o.source_order_id===x.source_order_id)),...transformed.records];
      setAllOrders(next);
      try{sessionStorage.setItem('guestlift-synthetic-orders',JSON.stringify(next.slice(0,2000)))}catch{/* session storage disabled */}
      setLastContents(contents);setResult(transformed);setSelectedOrder(transformed.records[0]?.source_order_id??'');setFilter('');
      setActiveStage(3);
      if(apiAvailable){
        const form=new FormData();
        for(const name of required)form.append('files',new Blob([contents[name]],{type:provider==='toast'?'text/csv':'application/json'}),name);
        const response=await fetch(`${api}/api/upload/${provider}`,{method:'POST',body:form});
        const answer=await response.json();
        if(!response.ok)throw new Error(answer.detail??'Local Python import failed');
        setLastApi({inserted:answer.inserted,duplicates:answer.duplicates,import_id:answer.import_id});
      }
      setActiveStage(4);
      setStatus(`${transformed.records.length} orders parsed from your files. ${apiAvailable?'Python adapter and local SQL import also completed.':'Processed in this browser; no server upload.'}`);
    }catch(e){setError(e instanceof Error?e.message:'Could not import files')}
    finally{setBusy(false)}
  }
  function reset(){setSelectedFiles([]);setSampleTexts(null);setLastContents(null);setResult(null);setAllOrders([]);setActiveStage(-1);setStatus('');setError('');setLastApi(null);setSelectedOrder('');try{sessionStorage.removeItem('guestlift-synthetic-orders')}catch{};if(fileInput.current)fileInput.current.value='';}
  async function resetLocalSql(){
    if(!apiAvailable||!window.confirm('Delete all imported orders from your LOCAL GuestLift demo database?'))return;
    try{const response=await fetch(`${api}/api/reset`,{method:'POST'});if(!response.ok)throw new Error('Reset failed');setLastApi(null);setStatus('Local demo SQL database cleared. Re-run the sample import to verify changes.');setError('');}
    catch(e){setError(e instanceof Error?e.message:'Could not reset the local database')}
  }
  const rawSource=useMemo(()=>{
    if(!inspected||!lastContents)return null;
    try{
      if(provider==='toast'){
        const id=inspected.source_order_id;
        return {
          OrderDetails:parseCsv(lastContents['OrderDetails.csv']).find(r=>r['Order Id']===id),
          ItemSelectionDetails:parseCsv(lastContents['ItemSelectionDetails.csv']).filter(r=>r['Order Id']===id),
          PaymentDetails:parseCsv(lastContents['PaymentDetails.csv']).filter(r=>r['Order Id']===id),
        };
      }
      const id=inspected.source_order_id;
      const orders=JSON.parse(lastContents['orders.json']).orders;
      const payments=JSON.parse(lastContents['payments.json']).payments;
      const refunds=JSON.parse(lastContents['refunds.json']).refunds;
      const matching=payments.filter((p:{order_id:string})=>p.order_id===id);
      const paymentIds=new Set(matching.map((p:{id:string})=>p.id));
      return {order:orders.find((o:{id:string})=>o.id===id),payments:matching,refunds:refunds.filter((r:{payment_id:string})=>paymentIds.has(r.payment_id))};
    }catch{return {error:'Unable to inspect source record'}}
  },[inspected,lastContents,provider]);
  const splitOrder=result?.records.find(o=>o.payments.length>1);
  const refundOrder=result?.records.find(o=>o.refund_minor>0);
  function inspectExample(order:Order|undefined){if(!order)return;setSelectedOrder(order.source_order_id);setInspectTab('source');document.getElementById('gl-record-audit')?.scrollIntoView({behavior:'smooth',block:'start'});}

  return <main className="gl-import-page">
    <section className="gl-import-hero"><div className="site-width gl-import-hero-row"><div><div className="gl-import-kicker"><span className="gl-dot gl-dot-teal"/> DATA IMPORT LAB / INTERACTIVE</div><h1>Don't just view a dashboard.<br/><em>Put data through it.</em></h1><p>Download a synthetic POS export, upload it here, and inspect every step from raw records to verified restaurant metrics.</p><div className="gl-import-hero-notes"><span><LockKeyhole size={15}/> Synthetic data only</span><span><CheckCircle2 size={15}/> Validation you can inspect</span></div></div><div className="gl-import-hero-symbol" aria-hidden="true"><div className="gl-flow-start"><span>TOAST</span><span>SQUARE</span></div><div className="gl-flow-tracks"><span/><span/></div><div className="gl-flow-core">GRDC</div><div className="gl-flow-arrow">→</div><div className="gl-flow-end">One report<br/><strong>✓</strong></div></div></div></section>

    <section className="site-width gl-import-container">
      <div className="gl-import-guide"><span><b>01</b> Choose provider</span><ArrowRight size={15}/><span><b>02</b> Upload files</span><ArrowRight size={15}/><span><b>03</b> Run pipeline</span><ArrowRight size={15}/><span><b>04</b> Inspect results</span></div>
      <div className="gl-import-grid">
        <div className="gl-import-left">
          <section className="gl-import-card"><div className="gl-card-kicker">STEP 01 — DATA SOURCE</div><h2>Which POS format?</h2><p>Each adapter knows a different format, but they both generate the same GuestLift data contract.</p><div className="gl-source-cards">{names.map(s=><button type="button" key={s.id} className={'gl-source-card '+(provider===s.id?'chosen':'')} onClick={()=>changeProvider(s.id)} aria-pressed={provider===s.id}><span className="gl-source-icon">{s.id==='toast'?'t':'■'}</span><span><strong>{s.name}</strong><small>{s.format}</small></span>{provider===s.id?<CheckCircle2 size={19}/>:<span className="gl-source-empty"/>}</button>)}</div><div className="gl-small-note"><Info size={15}/>{provider==='toast'?'Three related CSVs, not one flat order table.':'Orders, payments and refunds are separate JSON files.'}</div></section>

          <section className="gl-import-card"><div className="gl-card-kicker">STEP 02 — INPUT FILES</div><h2>Try the actual import</h2><p>Start with downloadable fabricated data, or edit it yourself and upload the new files.</p><div className="gl-file-actions"><a href={`/samples/${provider}-demo.zip`} download className="gl-sample-link"><Download size={17}/> Download {provider==='toast'?'Toast CSV':'Square JSON'} sample pack</a><button type="button" className="gl-sample-secondary" onClick={loadDemo} disabled={busy}><Play size={15}/> Load samples automatically</button></div><div className="gl-upload-drop"><UploadCloud size={29}/><strong>Upload {required.length} source files</strong><p>Choose the files from your extracted sample ZIP, or your own edited synthetic fixtures.</p><input ref={fileInput} type="file" multiple accept={provider==='toast'?'.csv':'.json'} onChange={e=>uploadChosen(e.target.files)} aria-label="Select POS fixture files"/><small>UTF-8 · up to 2 MB each · no personal or payment-card information</small></div><div className="gl-required-files"><span>Required filenames</span>{required.map(f=><div key={f}><FileSpreadsheet size={15}/>{f}{chosen&&f in chosen?<Check size={16} className="gl-file-valid"/>:<span className="gl-file-missing">Not selected</span>}</div>)}</div><div className="gl-import-actions"><button type="button" className="gl-primary-cta gl-run-import" onClick={run} disabled={busy}><FileUp size={18}/>{busy?'Processing…':'Run import pipeline'} <ArrowRight size={17}/></button><button type="button" className="gl-reset-import" onClick={reset}><RotateCcw size={16}/> Clear page</button></div><p className="gl-import-safety"><LockKeyhole size={14}/>{apiAvailable?'Local FastAPI detected: validated files will also be sent to your Docker backend and stored in local SQL.':'Public browser mode: these files are processed locally in your browser, not uploaded to any server.'}</p>{apiAvailable&&<button type="button" className="gl-sql-reset" onClick={resetLocalSql}><RotateCcw size={14}/> Reset local demo SQL (for re-importing edited orders)</button>}{error&&<div className="gl-import-error" role="alert"><ShieldAlert size={20}/>{error}</div>}{status&&<div className="gl-import-success" role="status"><CheckCircle2 size={20}/>{status}</div>}</section>
        </div>
        <div className="gl-import-right">
          <section className="gl-import-card gl-pipeline-card"><div className="gl-pipeline-head"><div><div className="gl-card-kicker">STEP 03 — TRANSFORM</div><h2>Inside your pipeline</h2></div><span className="gl-execution-mode">{apiAvailable?'Local API + PostgreSQL':'In-browser transformation'}</span></div><div className="gl-import-stages">{stages.map((s,i)=>{const Icon=s.icon;return <div className={'gl-import-stage '+(activeStage>=i?'done':'')} key={s.name}><div className="gl-import-stage-icon"><Icon size={18}/></div><div><strong>{s.name}</strong><span>{s.detail}</span></div>{activeStage>=i?<CheckCircle2 size={18}/>:<span className="gl-stage-id">0{i+1}</span>}</div>})}</div><div className="gl-pipeline-footnote">{result?'The parser processed the files shown on the left. These are calculated results.':'No import run yet. Select the sample files and run the pipeline.'}</div></section>

          <section className="gl-import-card gl-report-card"><div className="gl-pipeline-head"><div><div className="gl-card-kicker">STEP 04 — ANALYZE</div><h2>Imported order results</h2></div>{result&&<span className="gl-result-count">{result.summary.orders} accepted</span>}</div>{!result?<div className="gl-import-empty"><BarChart3 size={35}/><strong>Results appear here</strong><p>The dashboard isn't an illustration. Its figures update after you run your selected input files.</p></div>:<>
              <div className="gl-import-metric-grid"><div><span>Accepted orders</span><strong>{result.summary.orders}</strong><small>{result.summary.items} item lines · {result.summary.payments} payments</small></div><div><span>Pretax net sales</span><strong>{usd(result.summary.net_sales_minor)}</strong><small>Calculated from imported line items</small></div><div><span>Discounts</span><strong>{usd(result.summary.discounts_minor)}</strong><small>Order-level discounts</small></div><div><span>Sales refunds</span><strong>{usd(result.summary.refunds_minor)}</strong><small>Completed / recorded refunds</small></div></div>
              <div className="gl-import-quality"><CheckCircle2 size={17}/><span><b>{result.summary.orders} orders parsed</b> · 0 rejected {result.warnings.length?`· ${result.warnings.length} warnings`:''}</span></div>
              {lastApi&&<div className="gl-sql-confirm"><Database size={17}/> Local SQL: {lastApi.inserted} new · {lastApi.duplicates} existing · import #{lastApi.import_id}</div>}
              <div className="gl-import-examples"><strong>Explore real ingestion edge cases</strong><div><button type="button" disabled={!splitOrder} onClick={()=>inspectExample(splitOrder)}><Receipt size={15}/> Split payments <span>{splitOrder?splitOrder.source_order_id:'Not in this file'}</span></button><button type="button" disabled={!refundOrder} onClick={()=>inspectExample(refundOrder)}><RotateCcw size={15}/> Refunded order <span>{refundOrder?refundOrder.source_order_id:'Not in this file'}</span></button></div></div>
              <div className="gl-import-bar-title"><strong>Sales by location</strong><small>Derived from the uploaded records</small></div><div className="gl-import-location-bars">{totals.locations.slice(0,8).map(l=><div key={l.location_id}><span>{l.location_id}</span><div className="gl-location-track"><div style={{width:`${100*l.net_sales_minor/maxLocation}%`}}/></div><b>{usd(l.net_sales_minor)}</b></div>)}</div>
            </>}</section>
        </div>
      </div>
      {result&&<section id="gl-record-audit" className="gl-import-card gl-inspect-card"><div className="gl-inspect-heading"><div><div className="gl-card-kicker">AUDIT TRAIL / LINEAGE</div><h2>Inspect the actual records</h2><p>Click any order to see exactly how the source was translated into GRDC.</p></div><Link href="/offers?source=both&dataset=imported" className="gl-primary-cta">Model an offer on these orders <TicketPercent size={18}/></Link></div><div className="gl-inspect-grid"><div className="gl-inspect-list"><label><Search size={17}/><input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Search orders or locations…"/></label><div className="gl-inspect-list-body">{displayed.slice(0,100).map(o=><button type="button" key={o.source_order_id} onClick={()=>setSelectedOrder(o.source_order_id)} className={inspected?.source_order_id===o.source_order_id?'selected':''}><div><b>{o.source_order_id}</b><small>{o.location_id}</small></div><strong>{usd(o.net_sales_minor)}</strong><ChevronDown size={14}/></button>)}{displayed.length===0&&<p>No matches.</p>}</div></div><div className="gl-inspect-detail"><div className="gl-inspect-tabs"><button type="button" className={inspectTab==='grdc'?'active':''} onClick={()=>setInspectTab('grdc')}><Code2 size={15}/> Canonical GRDC</button><button type="button" className={inspectTab==='source'?'active':''} onClick={()=>setInspectTab('source')}><FileJson2 size={15}/> Source lineage</button></div><pre>{inspected?(inspectTab==='grdc'?shortJson(inspected):JSON.stringify(rawSource??{source_files:inspected.lineage},null,2)):'No order selected'}</pre></div></div>{result.warnings.length>0&&<details className="gl-warning-list"><summary><ShieldAlert size={16}/> {result.warnings.length} field coverage or reconciliation warning(s)</summary><ul>{result.warnings.slice(0,30).map((x,i)=><li key={i}>{x}</li>)}</ul></details>}</section>}
      <div className="gl-import-final-note"><ShieldAlert size={20}/><div><strong>Demo-only financial model.</strong> These are vendor-shaped fabricated files, not verified exports from a real merchant. No loyalty members, card numbers or real restaurant transactions. Actual refunds, voids and tender reconciliation require vendor-specific verification before a real pilot.</div></div>
    </section>
  </main>;
}
