'use client';

import Link from 'next/link';
import {useEffect,useMemo,useRef,useState} from 'react';
import {
  ArrowRight,ArrowUpRight,BarChart3,Check,CheckCircle2,ChevronDown,ClipboardCheck,Code2,
  Database,Download,FileCheck2,FileSpreadsheet,FileUp,Info,Layers3,LockKeyhole,
  MinusCircle,Receipt,RefreshCcw,Search,ShieldAlert,SlidersHorizontal,TicketPercent,Users,Wallet,X
} from 'lucide-react';
import fallback from '@/lib/demo-fallback.json';
import sample from '@/lib/campaign-demo.json';
import type {Order} from '@/lib/types';
import {usd} from '@/lib/types';
import {evaluateCampaigns} from '@/lib/campaign-model.mjs';
import type {CampaignAnalysis, CampaignReport} from '@/lib/campaign-model.mjs';

type Source='bundled'|'imported';
const baseOrders=[...(fallback.toast.records as Order[]),...(fallback.square.records as Order[])];
const API=process.env.NEXT_PUBLIC_GUESTLIFT_API_URL||'http://localhost:8000';
const dollars=(value:number)=>usd(value);
const numeral=(value:number)=>new Intl.NumberFormat('en-US').format(value);
const csvDownload=(content:string,name:string)=>{
  const link=document.createElement('a');const url=URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8'}));
  link.href=url;link.download=name;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
};

function AnalyzeStep({n,title,detail,done=false}:{n:string;title:string;detail:string;done?:boolean}){
 return <div className={'gc-step '+(done?'is-done':'')}><span className="gc-step-num">{done?<Check size={16}/>:n}</span><span><strong>{title}</strong><small>{detail}</small></span></div>;
}

export default function CampaignLab(){
 const [source,setSource]=useState<Source>('bundled');
 const [imported,setImported]=useState<Order[]>([]);
 const [campaignCsv,setCampaignCsv]=useState<string>(sample.campaigns_csv);
 const [redemptionCsv,setRedemptionCsv]=useState<string>(sample.redemptions_csv);
 const [filesSelected,setFilesSelected]=useState<string[]>([]);
 const [margin,setMargin]=useState(35);
 const [active,setActive]=useState('CAMP-LUNCH');
 const [filter,setFilter]=useState('');
 const [error,setError]=useState('');
 const [dataOrigin,setDataOrigin]=useState('Bundled fictional files');
 const [apiReady,setApiReady]=useState(false);
 const [apiBusy,setApiBusy]=useState(false);
 const [apiInfo,setApiInfo]=useState('');
 const [showIssues,setShowIssues]=useState(false);
 const campaignInput=useRef<HTMLInputElement>(null);
 const redemptionInput=useRef<HTMLInputElement>(null);
 useEffect(()=>{
   try{const saved=sessionStorage.getItem('guestlift-synthetic-orders');if(saved){const arr=JSON.parse(saved);
     if(Array.isArray(arr)){const valid=arr.filter(o=>o && ['toast','square'].includes(o.provider)&&typeof o.source_order_id==='string'&&Number.isSafeInteger(o.net_sales_minor)&&Array.isArray(o.items));setImported(valid)}}}
   catch{/* Browser storage not available. */}
   const controller=new AbortController();
   fetch(`${API}/api/health`,{signal:controller.signal}).then(r=>r.ok?r.json():null).then(x=>{if(x?.mode==='synthetic_demo')setApiReady(true)}).catch(()=>{});
   return ()=>controller.abort();
 },[]);
 const orders=source==='imported'?imported:baseOrders;
 const result=useMemo<CampaignAnalysis|null>(()=>{
   try{return evaluateCampaigns(orders,campaignCsv,redemptionCsv,margin)}catch(e){return null}
 },[orders,campaignCsv,redemptionCsv,margin]);
 const activeCampaign=result?.campaigns.find(x=>x.campaign_id===active)||result?.campaigns[0]||null;
 const searched=activeCampaign?.order_matches.filter(x=>
   `${x.redemption_id} ${x.source_order_id} ${x.location_id} ${x.provider} ${x.customer_id||''}`.toLowerCase().includes(filter.toLowerCase()))||[];
 const csvReport=()=>{
   if(!result)return;
   const header=['campaign_id','code','redeemed_orders','attributed_net_sales_minor','recorded_discount_minor','modeled_contribution_minor','margin_assumption_percent'];
   const rows=result.campaigns.map(x=>[x.campaign_id,x.code,x.redeemed_orders,x.attributed_net_sales_minor,x.recorded_discount_minor,x.modeled_contribution_minor,margin]);
   csvDownload([header,...rows].map(row=>row.join(',')).join('\n'),'guestlift-campaign-report-SYNTHETIC.csv');
 };
 const readCsv=async(file:File|null,kind:'campaigns'|'redemptions')=>{
   setError('');setApiInfo('');if(!file)return;
   if(file.name!==(kind==='campaigns'?'Campaigns.csv':'Redemptions.csv')){setError(`Expected ${kind==='campaigns'?'Campaigns.csv':'Redemptions.csv'}, not ${file.name}`);return}
   if(file.size>2_000_000){setError('Maximum demonstration file size is 2 MB');return}
   try{const txt=await file.text();if(kind==='campaigns')setCampaignCsv(txt);else setRedemptionCsv(txt);
    setFilesSelected(s=>[...new Set([...s,kind])]);setDataOrigin('Files selected from your computer · processed in browser');
   }catch{setError('Cannot read file as text')}
 };
 const restore=()=>{
   setCampaignCsv(sample.campaigns_csv);setRedemptionCsv(sample.redemptions_csv);
   setSource('bundled');setFilesSelected([]);setMargin(35);setActive('CAMP-LUNCH');setDataOrigin('Bundled fictional files');setError('');setApiInfo('');
   if(campaignInput.current)campaignInput.current.value='';if(redemptionInput.current)redemptionInput.current.value='';
 };
 const syncLocal=async()=>{
   if(!apiReady){setApiInfo('Local API is not available. Browser calculations still work without it.');return}
   setApiBusy(true);setError('');setApiInfo('');
   try{
     // Included sample POS orders must exist in SQL before campaign records can match.
     if(source==='bundled'&&filesSelected.length===0){
       const response=await fetch(`${API}/api/campaigns/demo/load`,{method:'POST'});
       const body=await response.json();if(!response.ok)throw new Error(body.detail||'Local demonstration import failed');
       setApiInfo(`Verified in SQL: ${body.redemptions_inserted} new redemptions; ${body.duplicates} already imported; ${body.rejected} rejected. Your local DB is persistent.`);
     }else{
       const form=new FormData();
       form.append('campaigns_file',new File([campaignCsv],'Campaigns.csv',{type:'text/csv'}));
       form.append('redemptions_file',new File([redemptionCsv],'Redemptions.csv',{type:'text/csv'}));
       const response=await fetch(`${API}/api/campaigns/upload`,{method:'POST',body:form});
       const body=await response.json();if(!response.ok)throw new Error(body.detail||'Local upload failed');
       setApiInfo(`Local SQL: ${body.redemptions_inserted} accepted, ${body.duplicates} duplicates, ${body.rejected} rejected. Import POS orders into your local API first for custom matches.`);
     }
   }catch(e){setError(e instanceof Error?e.message:'Could not reach the local API')}finally{setApiBusy(false)}
 };
 const highlights=[
   {label:'Redeemed orders',value:activeCampaign?numeral(activeCampaign.redeemed_orders):'—',detail:'Orders matched by ID',tone:'indigo',icon:Receipt},
   {label:'Sales on redeemed orders',value:activeCampaign?dollars(activeCampaign.attributed_net_sales_minor):'—',detail:'Not incremental revenue',tone:'teal',icon:BarChart3},
   {label:'Recorded coupon discounts',value:activeCampaign?dollars(activeCampaign.recorded_discount_minor):'—',detail:'Already deducted from POS net sales',tone:'amber',icon:TicketPercent},
   {label:'Modeled contribution',value:activeCampaign?dollars(activeCampaign.modeled_contribution_minor):'—',detail:`${margin}% assumed margin · NOT ROI`,tone:'rose',icon:Wallet}
 ];
 return <main className="gc-page">
  <section className="gc-hero"><div className="site-width gc-hero-layout">
   <div><span className="gc-kicker"><span className="gc-kicker-pulse"/> GUESTLIFT CAMPAIGN INTELLIGENCE · V0.4</span>
    <h1>Know what your<br/><em>promotions cost.</em><br/>Then decide what’s next.</h1>
    <p>Bring together synthetic orders, coupon redemptions, and customer return activity. See the full calculation behind each campaign—without confusing redeemed sales with new sales.</p>
    <div className="gc-hero-actions"><a href="#workspace" className="gc-cta-main">Explore the working demo <ArrowUpRight size={17}/></a><a href="/samples/campaigns-demo.zip" download className="gc-cta-secondary"><Download size={17}/> Download sample campaigns</a></div>
    <span className="gc-proof"><LockKeyhole size={15}/> Fictional data only · Safe browser processing · No live POS access</span>
   </div>
   <div className="gc-hero-visual" aria-label="Data flowing from the two POS systems to campaign reporting">
    <div className="gc-hero-visual-header"><span>HOW THE INFORMATION CONNECTS</span><span><span className="gc-small-led"/> Demo environment</span></div>
    <div className="gc-streams"><div className="gc-stream"><span className="gc-provider-icon">t</span><div><strong>Toast orders</strong><small>CSV transactions</small></div><FileCheck2 size={17}/></div><div className="gc-stream"><span className="gc-provider-icon square">■</span><div><strong>Square orders</strong><small>JSON transactions</small></div><FileCheck2 size={17}/></div></div>
    <div className="gc-connection"><span/><span/><div>GRDC</div></div>
    <div className="gc-stream gc-stream-final"><span className="gc-provider-icon final"><TicketPercent size={22}/></span><div><strong>Campaign & customer intelligence</strong><small>21 fictional redemptions across 2 campaigns</small></div><CheckCircle2 size={18}/></div>
    <div className="gc-hero-visual-foot"><span>MATCHED BY ORDER ID</span><span>VALIDATED FINANCIAL FIELDS</span></div>
   </div>
  </div></section>
  <section id="workspace" className="site-width gc-workspace">
   <div className="gc-topline"><div><span className="gc-section-eyebrow">INTERACTIVE WORKSPACE</span><h2>A real workflow, with test data.</h2><p>Everything below is calculated from bundled or uploaded fictional records. Try changing the file contents to see errors and numbers update.</p></div><div className="gc-version"><CheckCircle2 size={17}/> Working browser demo <span>·</span> {apiReady?'Local API detected':'Static-safe'}</div></div>
   <div className="gc-process">
     <AnalyzeStep n="01" title="Import POS orders" detail={source==='bundled'?'56 bundled fictional orders':`${orders.length} recently imported`} done={orders.length>0}/>
     <AnalyzeStep n="02" title="Upload campaign files" detail="Campaigns + redemption events" done={Boolean(result)}/>
     <AnalyzeStep n="03" title="Match and audit" detail={result?`${result.total_redemptions} matched · ${result.rejected} rejected`:'Awaiting valid input'} done={Boolean(result)}/>
     <AnalyzeStep n="04" title="Make a decision" detail="Cost and return visits" done={Boolean(activeCampaign)}/>
   </div>
   <div className="gc-content">
    <div className="gc-settings">
     <section className="gc-panel"><div className="gc-panel-top"><span className="gc-step-label">01 / DATA SOURCE</span><Layers3 size={19}/></div><h3>Orders to analyze</h3><p>Use fictional POS transactions or orders you just loaded in the <Link href="/import">Import Lab</Link>.</p>
      <div className="gc-segment"><button className={source==='bundled'?'selected':''} onClick={()=>setSource('bundled')}>Built-in examples <span>{baseOrders.length}</span></button><button className={source==='imported'?'selected':''} onClick={()=>setSource('imported')} disabled={!imported.length}>Your last import <span>{imported.length||'—'}</span></button></div>
      <div className="gc-coverage"><span><CheckCircle2 size={16}/> {orders.length} orders available</span><Link href="/import">Import a POS file <ArrowUpRight size={13}/></Link></div>
     </section>
     <section className="gc-panel"><div className="gc-panel-top"><span className="gc-step-label">02 / COUPON RECORDS</span><TicketPercent size={19}/></div><h3>Import campaign activity</h3><p>Each redemption supplies a campaign ID, provider, order ID and the discount recorded by the POS.</p>
      <a href="/samples/campaigns-demo.zip" download className="gc-download"><Download size={16}/> Download campaign CSV pair <ArrowUpRight size={15}/></a>
      <label className="gc-upload-field"><span><FileSpreadsheet size={16}/> Campaigns.csv</span><input ref={campaignInput} type="file" accept=".csv" onChange={e=>readCsv(e.target.files?.[0]||null,'campaigns')}/><small>{filesSelected.includes('campaigns')?'Your selected file is loaded':'Using fictional bundled CSV'}</small></label>
      <label className="gc-upload-field"><span><FileSpreadsheet size={16}/> Redemptions.csv</span><input ref={redemptionInput} type="file" accept=".csv" onChange={e=>readCsv(e.target.files?.[0]||null,'redemptions')}/><small>{filesSelected.includes('redemptions')?'Your selected file is loaded':'Using fictional bundled CSV'}</small></label>
      <div className="gc-source-note"><LockKeyhole size={16}/><span>{dataOrigin}. <strong>Do not upload real customer data.</strong></span></div>
      <div className="gc-controls"><button onClick={restore}><RefreshCcw size={15}/> Restore sample</button><button onClick={syncLocal} disabled={apiBusy} className="gc-save-local"><Database size={15}/>{apiBusy?'Saving…':'Save to local SQL'}</button></div>
      {apiInfo&&<div className="gc-confirmation" role="status"><CheckCircle2 size={16}/>{apiInfo}</div>}{error&&<div className="gc-error" role="alert"><ShieldAlert size={16}/>{error}</div>}
     </section>
     <section className="gc-panel"><div className="gc-panel-top"><span className="gc-step-label">03 / ECONOMICS</span><SlidersHorizontal size={19}/></div><h3>Change the assumptions</h3><p>Contribution shown here is a hypothetical scenario. We don't have the restaurant's real food, labor, or fulfillment costs.</p>
      <div className="gc-slider-heading"><label htmlFor="gc-margin">Assumed contribution margin on net sales</label><strong>{margin}%</strong></div>
      <input id="gc-margin" type="range" min="0" max="90" step="5" value={margin} onChange={e=>setMargin(Number(e.target.value))}/>
      <div className="gc-slider-legend"><span>0%</span><span>45%</span><span>90%</span></div>
      <div className="gc-calculation">Net sales × {margin}% <span>−</span> added reward/fulfillment cost <span>−</span> allocated marketing cost.</div>
     </section>
    </div>
    <div className="gc-results">
     <section className="gc-panel gc-report">
      <div className="gc-report-toolbar"><div><span className="gc-step-label">04 / CAMPAIGN PERFORMANCE</span><h3>Promotion report</h3></div><button onClick={csvReport} disabled={!result}><Download size={16}/> Export CSV</button></div>
      {!result?<div className="gc-empty"><ShieldAlert size={30}/><strong>These files cannot be analyzed yet</strong><p>Check the CSV headers, campaign dates and money fields. Restore the sample files to start again.</p></div>:<>
       <div className="gc-campaign-tabs">{result.campaigns.map(c=><button key={c.campaign_id} onClick={()=>{setActive(c.campaign_id);setFilter('')}} className={activeCampaign?.campaign_id===c.campaign_id?'selected':''}><span className="gc-tab-dot"/><strong>{c.name}</strong><small>{c.code}</small></button>)}</div>
       {activeCampaign&&<>
        <div className="gc-selected-campaign"><div><span>SELECTED CAMPAIGN · {activeCampaign.code}</span><h4>{activeCampaign.name}</h4><p>{activeCampaign.description}</p></div><span className="gc-status"><CheckCircle2 size={14}/> Reconciled sample</span></div>
        <div className="gc-kpis">{highlights.map(item=>{const Icon=item.icon;return <div key={item.label} className={'gc-kpi '+item.tone}><div><span>{item.label}</span><Icon size={18}/></div><strong>{item.value}</strong><small>{item.detail}</small></div>})}</div>
        <div className="gc-insight"><Info size={20}/><div><strong>What the data can—and cannot—say</strong><p>{activeCampaign.redeemed_orders} orders contain valid recorded coupon matches. Their net sales were {dollars(activeCampaign.attributed_net_sales_minor)} after existing discounts and refunds. That does <b>not</b> tell us whether the campaign caused new visits or additional profit.</p></div></div>
        <div className="gc-report-lower"><div className="gc-locations"><h4>Where coupons were used</h4><p>Sales on matched orders, grouped by POS location.</p>{activeCampaign.locations.length?activeCampaign.locations.map(l=>{const max=Math.max(...activeCampaign.locations.map(x=>x.net_sales_minor),1);return <div className="gc-location-line" key={l.provider+':'+l.location_id}><span>{l.location_id}</span><div><i style={{width:Math.max(2,100*l.net_sales_minor/max)+'%'}}/></div><b>{dollars(l.net_sales_minor)}</b></div>}):<span className="gc-muted">No recorded matches for this campaign.</span>}</div>
         <div className="gc-people"><h4>Repeat customers</h4><p>Only synthetic customer IDs that are present in the selected POS records.</p><div className="gc-circle-metric"><div>{result.customer_summary.repeat_customer_rate_percent}%</div><span>of identified<br/>customers repeat</span></div><div className="gc-people-rows"><span>Identified customers <b>{result.customer_summary.identified_customers}</b></span><span>Repeat customers <b>{result.customer_summary.repeat_customers}</b></span><span>Anonymous orders <b>{result.customer_summary.anonymous_orders}</b></span></div><small>Customer identities are scoped within each provider, not merged between Toast and Square.</small></div>
        </div>
       </>}
      </>}
     </section>
     {result&&<section className="gc-panel gc-audit"><div className="gc-report-toolbar"><div><span className="gc-step-label">AUDITABILITY</span><h3>Trace each coupon to its order</h3></div><span className="gc-audit-count">{activeCampaign?.order_matches.length||0} matched records</span></div>
      <label className="gc-search"><Search size={17}/><input placeholder="Search order IDs, providers or locations" value={filter} onChange={e=>setFilter(e.target.value)}/></label>
      <div className="gc-table-wrap"><table className="gc-table"><thead><tr><th>Order</th><th>Source / location</th><th>Discount</th><th>Net sales</th><th>Identity</th></tr></thead><tbody>{searched.length?searched.map(x=><tr key={x.redemption_id}><td><strong>{x.source_order_id}</strong><small>{x.redemption_id}</small></td><td><span className="gc-provider-label">{x.provider}</span><small>{x.location_id}</small></td><td>{dollars(x.recorded_discount_minor)}</td><td>{dollars(x.net_sales_minor)}</td><td>{x.customer_id?<span className="gc-tag-green">Known test ID</span>:<span className="gc-tag-muted">Anonymous</span>}</td></tr>):<tr><td colSpan={5}>No matching orders.</td></tr>}</tbody></table></div>
      {result.rejected>0&&<details className="gc-validation" open={showIssues} onToggle={e=>setShowIssues(e.currentTarget.open)}><summary><ShieldAlert size={17}/>{result.rejected} validation issue(s) in the uploaded CSVs <ChevronDown size={16}/></summary><ul>{result.issues.map((issue,i)=><li key={i}>{issue}</li>)}</ul></details>}
     </section>}
    </div>
   </div>
   <div className="gc-principle"><div><MinusCircle size={22}/><strong>Not an incrementality report</strong></div><p>A coupon redeemed on an order doesn't prove that the order would not have happened otherwise. To calculate causal incremental profit, a restaurant would need a valid comparison group, costs, and a careful experiment. GuestLift v0.4 reports observed redemptions and clearly labeled hypothetical contribution only.</p><Link href="/how-it-works">Explore the underlying pipeline <ArrowRight size={17}/></Link></div>
  </section>
 </main>;
}
