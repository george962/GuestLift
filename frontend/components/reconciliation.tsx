'use client';
import {useCallback,useEffect,useState} from 'react';
import {Download} from 'lucide-react';
import {accountApi} from '@/lib/local-auth';

export type ReconRow={location_id:string;location:string;date:string;orders:number;gross_sales_minor:number;discounts_minor:number;
  refunds_minor:number;net_sales_minor:number;tax_minor:number;tips_minor:number};
export type ReconTotal={location_id:string;location:string;orders:number;gross_sales_minor:number;discounts_minor:number;
  refunds_minor:number;net_sales_minor:number;tax_minor:number;tips_minor:number};
export type Reconciliation={start:string;end:string;days:ReconRow[];totals:ReconTotal[];definitions:Record<string,string>;how_to_compare:string};

const money=(n:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
const iso=(d:Date)=>d.toISOString().slice(0,10);
const COLS:[keyof ReconTotal,string][]=[['orders','Orders'],['gross_sales_minor','Gross sales'],['discounts_minor','Discounts'],
 ['refunds_minor','Refunds'],['net_sales_minor','Net sales'],['tax_minor','Tax'],['tips_minor','Tips']];
const cell=(k:keyof ReconTotal,v:number)=>k==='orders'?v.toLocaleString('en-US'):money(v);

/** "Check against Square": our totals per location and day, laid out like Square's Sales Summary. */
export function ReconciliationPanel({token,refreshKey}:{token:string;refreshKey?:string|null}){
 const today=new Date();const yesterday=new Date(Date.UTC(today.getUTCFullYear(),today.getUTCMonth(),today.getUTCDate()-1));
 const [start,setStart]=useState(iso(new Date(yesterday.getTime()-6*864e5)));
 const [end,setEnd]=useState(iso(yesterday));
 const [data,setData]=useState<Reconciliation|null>(null);
 const [error,setError]=useState('');
 const load=useCallback(async()=>{setError('');
  try{setData(await accountApi(`/api/integrations/square/reconciliation?start=${start}&end=${end}`,token) as Reconciliation)}
  catch(e){setError(e instanceof Error?e.message:'Could not load the comparison.')}},[start,end,token,refreshKey]);
 useEffect(()=>{void load()},[load]);
 function csv(){
  if(!data)return;
  const head=['Location','Date',...COLS.map(c=>c[1])];
  const lines=[head,...data.days.map(r=>[r.location,r.date,...COLS.map(([k])=>k==='orders'?String(r[k]):(Number(r[k])/100).toFixed(2))])];
  const blob=new Blob([lines.map(l=>l.map(v=>`"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n')],{type:'text/csv'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`tablesignal-${start}-to-${end}.csv`;a.click();URL.revokeObjectURL(a.href);
 }
 return <section className="ts9-panel" aria-labelledby="recon-h">
  <span className="ts9-kicker">ACCURACY CHECK</span><h3 id="recon-h">Check against Square</h3>
  <p className="ts9-muted">{data?.how_to_compare||'Compare these totals with Square Dashboard → Reports → Sales summary for the same dates.'} Days use each location's own time zone.</p>
  <div className="ts9-inline-actions">
   <label>From <input type="date" id="recon-start" value={start} max={end} onChange={e=>setStart(e.target.value)}/></label>
   <label>To <input type="date" id="recon-end" value={end} min={start} onChange={e=>setEnd(e.target.value)}/></label>
   <button className="ts9-button secondary" disabled={!data?.days.length} onClick={csv}><Download size={16}/> Download CSV</button>
  </div>
  {error&&<div className="ts9-notice danger" role="alert">{error}</div>}
  {data&&(data.totals.length===0?<p>No completed orders in these dates.</p>:
  <div role="region" aria-label="Square totals by location (scroll horizontally)" tabIndex={0} style={{overflowX:'auto'}}><table className="ts9-table" aria-label="Totals by location">
   <thead><tr><th scope="col">Location</th>{COLS.map(([,l])=><th key={l} scope="col" style={{textAlign:'right'}}>{l}</th>)}</tr></thead>
   <tbody>{data.totals.map(t=><tr key={t.location_id} data-location={t.location_id}><th scope="row">{t.location}</th>
    {COLS.map(([k])=><td key={k} data-col={k} style={{textAlign:'right',fontVariantNumeric:'tabular-nums'}}>{cell(k,Number(t[k]))}</td>)}</tr>)}</tbody>
  </table></div>)}
  {data&&data.days.length>0&&<details><summary>Show each day</summary><div role="region" aria-label="Square daily totals (scroll horizontally)" tabIndex={0} style={{overflowX:'auto'}}><table className="ts9-table">
   <thead><tr><th scope="col">Location</th><th scope="col">Date</th>{COLS.map(([,l])=><th key={l} scope="col" style={{textAlign:'right'}}>{l}</th>)}</tr></thead>
   <tbody>{data.days.map(r=><tr key={r.location_id+r.date}><td>{r.location}</td><td>{r.date}</td>
    {COLS.map(([k])=><td key={k} style={{textAlign:'right',fontVariantNumeric:'tabular-nums'}}>{cell(k,Number(r[k as keyof ReconRow]))}</td>)}</tr>)}</tbody>
  </table></div></details>}
 </section>;
}
