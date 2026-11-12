'use client';

import {useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,ArrowUpRight,Calculator,CheckCircle2,ChevronDown,FileSpreadsheet,Info,LockKeyhole,Percent,Receipt,ShieldAlert,SlidersHorizontal,Store,TicketPercent,TrendingUp,Wallet} from 'lucide-react';
import data from '@/lib/demo-fallback.json';
import type {Order,Provider} from '@/lib/types';
import {usd} from '@/lib/types';
import {evaluateOffer} from '@/lib/offer-model.mjs';

type SourceChoice='both'|Provider;
type OfferType='percent'|'fixed'|'free_item';
const allOrders=[...(data.toast.records as Order[]),...(data.square.records as Order[])];
const numeric=(v:string,min:number,max:number)=>{
  const n=Number(v);
  return Number.isFinite(n)?Math.min(max,Math.max(min,n)):min;
};

export default function Offers(){
  const [source,setSource]=useState<SourceChoice>('both');
  const [offerType,setOfferType]=useState<OfferType>('percent');
  const [name,setName]=useState('LUNCH10');
  const [amount,setAmount]=useState('10');
  const [minimum,setMinimum]=useState('15');
  const [margin,setMargin]=useState('35');
  const [showRows,setShowRows]=useState(false);
  useEffect(()=>{
    const requested=new URLSearchParams(window.location.search).get('source');
    if(requested==='toast'||requested==='square'||requested==='both')setSource(requested);
  },[]);
  const orders=useMemo(()=>source==='both'?allOrders:allOrders.filter(o=>o.provider===source),[source]);
  const config=useMemo(()=>({
    type:offerType,
    value:numeric(amount,0,100),
    amountMinor:Math.round(numeric(amount,0,10000)*100),
    minimumMinor:Math.round(numeric(minimum,0,10000)*100),
    marginPercent:numeric(margin,0,95)
  }),[offerType,amount,minimum,margin]);
  const result=useMemo(()=>evaluateOffer(orders,config),[orders,config]);
  const sourceText=source==='both'?'Toast + Square samples':source==='toast'?'Toast sample orders':'Square sample orders';
  const formattedDescription=offerType==='percent'?`${numeric(amount,0,100)}% off` : offerType==='fixed'?`${usd(config.amountMinor)} off`:`Free item (estimated cost ${usd(config.amountMinor)})`;
  return <main className="gl-offer-page">
    <section className="gl-offer-head site-width">
      <div className="gl-breadcrumb"><Link href="/">Home</Link><ArrowRight size={13}/><span>Offer studio</span></div>
      <div className="gl-offer-head-layout"><div>
        <div className="gl-eyebrow"><span className="gl-dot gl-dot-amber"/> THE CAMPAIGN WORKSPACE · INTERACTIVE DEMO</div>
        <h1>Make the offer.<br/><em>Know the tradeoff.</em></h1>
        <p>See how a restaurant operator could use standardized POS orders to explore a coupon, free item, or loyalty perk—and understand its cost before making promises about performance.</p>
      </div><div className="gl-provenance"><ShieldAlert size={20}/><div><strong>Safe, fictional demo</strong><span>No customer uploads or personal information. All orders are fabricated. Scenarios are not evidence of increased purchases or profit.</span></div></div></div>
    </section>
    <section className="gl-studio site-width">
      <div className="gl-studio-guide"><span><b>01</b> Choose sample orders</span><ArrowRight size={16}/><span><b>02</b> Define your offer</span><ArrowRight size={16}/><span><b>03</b> See the economics</span></div>
      <div className="gl-studio-grid">
        <div className="gl-controls-col">
          <section className="gl-surface gl-control-panel"><div className="gl-panel-title"><div className="gl-mini-icon gl-indigo"><FileSpreadsheet size={19}/></div><div><span className="gl-eyebrow">STEP 01 / YOUR DATA</span><h2>Choose an order source</h2></div></div>
            <p className="gl-panel-copy">A real operator would authorize an import. For this public demo, choose preloaded, synthetic Toast- or Square-shaped records.</p>
            <div className="gl-select-grid" role="group" aria-label="Sample POS data">
              {([{id:'both',label:'Both sources',desc:'Combined view',glyph:'↔'},{id:'toast',label:'Toast POS',desc:'CSV-shaped',glyph:'t'},{id:'square',label:'Square POS',desc:'API-shaped',glyph:'■'}] as const).map(x=><button key={x.id} type="button" aria-pressed={source===x.id} className={'gl-choice '+(source===x.id?'active':'')} onClick={()=>setSource(x.id)}><span className="gl-choice-icon">{x.glyph}</span><strong>{x.label}</strong><small>{x.desc}</small>{source===x.id&&<CheckCircle2 className="gl-choice-check" size={16}/>}</button>)}
            </div>
            <div className="gl-mini-success"><CheckCircle2 size={17}/><span>{orders.length} standardized example orders selected</span><Link href="/demo">Inspect pipeline <ArrowUpRight size={13}/></Link></div>
          </section>
          <section className="gl-surface gl-control-panel"><div className="gl-panel-title"><div className="gl-mini-icon gl-amber"><TicketPercent size={19}/></div><div><span className="gl-eyebrow">STEP 02 / YOUR OFFER</span><h2>Configure the promotion</h2></div></div>
            <div className="gl-fields">
              <label className="gl-field"><span>Campaign name or coupon code</span><input maxLength={28} value={name} onChange={e=>setName(e.target.value.replace(/[^a-zA-Z0-9_-]/g,''))} placeholder="LUNCH10"/><small>Used to label this scenario. No actual redemptions are matched.</small></label>
              <fieldset className="gl-fieldset"><legend>Offer type</legend><div className="gl-type-switch">
                {([{id:'percent',label:'% Discount'},{id:'fixed',label:'$ Discount'},{id:'free_item',label:'Free item'}] as const).map(x=><button aria-pressed={offerType===x.id} className={offerType===x.id?'selected':''} key={x.id} onClick={()=>{setOfferType(x.id);setAmount(x.id==='percent'?'10':x.id==='fixed'?'3':'2.25')}} type="button">{x.label}</button>)}
              </div></fieldset>
              <div className="gl-field-row"><label className="gl-field"><span>{offerType==='percent'?'Percent off':offerType==='fixed'?'Discount amount ($)':'Estimated unit cost ($)'}</span><div className="gl-input-icon"><input type="number" inputMode="decimal" value={amount} min="0" max={offerType==='percent'?'100':'10000'} step="0.25" onChange={e=>setAmount(e.target.value)}/><span>{offerType==='percent'?'%':'USD'}</span></div></label><label className="gl-field"><span>Minimum qualifying order ($)</span><input type="number" inputMode="decimal" value={minimum} min="0" step="1" onChange={e=>setMinimum(e.target.value)}/></label></div>
              <label className="gl-field"><span>Assumed pre-offer contribution margin (%) <span className="gl-inline-hint" title="Simplified assumption, not actual food cost data."><Info size={13}/></span></span><div className="gl-input-icon"><input type="number" value={margin} min="0" max="95" step="1" onChange={e=>setMargin(e.target.value)}/><span>%</span></div><small>Includes assumed variable costs. This is an editable assumption—not imported POS data.</small></label>
            </div>
          </section>
        </div>
        <div className="gl-results-col">
          <section className="gl-surface gl-offer-results"><div className="gl-result-header"><div><span className="gl-eyebrow">STEP 03 / MODELLED ECONOMICS</span><h2>{name||'Untitled offer'}</h2><p>{formattedDescription} · Minimum {usd(config.minimumMinor)} · {sourceText}</p></div><span className="gl-status gl-status-demo"><span/> SAMPLE SCENARIO</span></div>
            <div className="gl-stats-grid"><div className="gl-stat"><div className="gl-stat-heading"><Receipt size={17}/><span>Qualifying orders</span></div><strong>{result.eligibleCount} <small>/ {result.orderCount}</small></strong><p>Historical sample baskets meeting your threshold</p></div><div className="gl-stat gl-stat-amber"><div className="gl-stat-heading"><Wallet size={17}/><span>Modeled offer cost</span></div><strong>{usd(result.offerCostMinor)}</strong><p>Extra discounts plus reward unit costs</p></div><div className="gl-stat"><div className="gl-stat-heading"><TrendingUp size={17}/><span>Sales after offer</span></div><strong>{usd(result.modeledNetMinor)}</strong><p>Same orders, after hypothetical added discount</p></div><div className="gl-stat gl-stat-rose"><div className="gl-stat-heading"><Calculator size={17}/><span>Added orders to break even</span></div><strong>{result.breakEvenAddedOrders===null?'Not feasible':result.breakEvenAddedOrders}</strong><p>Assumes added orders have the same average basket, offer cost and margin; not a traffic forecast</p></div></div>
            <div className="gl-analysis-divider"/>
            <div className="gl-assumption-header"><div><h3>What this coupon changes</h3><p>All qualifying sample orders are assumed to redeem once, with no change in their purchase behavior. The new offer is applied on top of any discounts already in the source data.</p></div></div>
            <div className="gl-compare"><div><span>Baseline sample net sales</span><strong>{usd(result.baseNetMinor)}</strong><div className="gl-track"><div className="gl-fill gl-fill-base" style={{width:'100%'}}/></div></div><div><span>After hypothetical offer</span><strong>{usd(result.modeledNetMinor)}</strong><div className="gl-track"><div className="gl-fill gl-fill-offer" style={{width:`${result.baseNetMinor?100*result.modeledNetMinor/result.baseNetMinor:0}%`}}/></div></div></div>
            <div className="gl-insight"><ShieldAlert size={20}/><div><b>Does the promotion bring in more customers?</b><p>We cannot tell from these transactions. To measure incremental visits and profit, the restaurant would need eligible customer assignments, a control group or credible alternative design, and actual cost data.</p></div></div>
            <button type="button" className="gl-details-toggle" onClick={()=>setShowRows(v=>!v)} aria-expanded={showRows}>{showRows?'Hide':'See'} order-level assumptions <ChevronDown size={17} className={showRows?'gl-flip':''}/></button>
            {showRows&&<div className="gl-offer-table-wrap"><table className="gl-offer-table"><thead><tr><th>Order</th><th>POS</th><th>Base</th><th>Added cost</th></tr></thead><tbody>{result.details.slice(0,12).map(d=><tr key={`${d.provider}-${d.orderId}`}><td>{d.orderId}</td><td>{d.provider}</td><td>{usd(d.baseNetMinor)}</td><td>{usd(d.incrementalDiscountMinor+d.extraRewardCostMinor)}</td></tr>)}</tbody></table>{result.details.length>12&&<p>Showing 12 of {result.details.length} qualifying orders.</p>}{result.details.length===0&&<p>No sample orders meet the selected minimum.</p>}</div>}
          </section>
          <section className="gl-next-panel"><div className="gl-mini-icon gl-teal"><CheckCircle2 size={19}/></div><div><h3>What would happen with a real restaurant?</h3><p>After authorized POS data and campaign identifiers are connected, GuestLift could identify documented redemptions, trace discounts to orders, and eventually run genuine holdout-based lift analysis.</p><Link href="/how-it-works">See the ingestion architecture <ArrowUpRight size={16}/></Link></div></section>
        </div>
      </div>
      <div className="gl-notes"><LockKeyhole size={18}/><p><strong>Privacy-first demonstration.</strong> This public experience runs entirely on fabricated records bundled with the website. It never uploads restaurant data or stores your coupon settings on a server. The installed local developer API is separate.</p></div>
    </section>
  </main>;
}
