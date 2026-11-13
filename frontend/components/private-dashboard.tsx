'use client';

import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight, BarChart3, CheckCircle2, CreditCard, Database, Info, RefreshCcw,
  ShieldCheck, Sparkles, Store, TicketPercent, TrendingUp, Users, Wallet} from 'lucide-react';
import {accountApi, localAuthClient} from '@/lib/local-auth';

// Account-backed metrics only. No bundled sample orders are imported on this route.
type LocationMetric={location:string;orders:number;net_sales_minor:number;discount_minor:number};
type DailyMetric={date:string;orders:number;net_sales_minor:number};
type Summary={data_origin:string;has_connected_source:boolean;orders:number;net_sales_minor:number;
  discount_minor:number;average_order_minor:number;identified_orders:number;anonymous_orders:number;
  identification_coverage_percent:number;identified_customers:number;repeat_customers:number;
  repeat_customer_rate_percent:number|null;locations:LocationMetric[];daily:DailyMetric[];
  campaigns:{code:string;redemptions:number;discount_minor:number}[];methodology:Record<string,string>};
type Workspace={name:string;restaurant_type:string;goal:string;plan:string;subscription_status:string;
  ai_enabled:boolean;source_mode:string};
type Account={workspace:Workspace;summary:Summary};
type Tab='overview'|'guests'|'promotions'|'analyst';
const money=(n:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
const count=(n:number)=>new Intl.NumberFormat('en-US').format(n);
const questions=['Summarize my sales','What do we know about returning customers?',
  'Which locations have the most sales?','What can we tell about promotions?'];

export function PrivateDashboard({initialTab='overview'}:{initialTab?:Tab}){
  const [tab,setTab]=useState<Tab>(initialTab);
  const [data,setData]=useState<Account|null>(null);
  const [token,setToken]=useState('');
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [question,setQuestion]=useState(questions[0]);
  const [answer,setAnswer]=useState<{answer:string;evidence_keys:string[];recommended_next_step:string;engine:string}|null>(null);
  const [busy,setBusy]=useState(false);

  const refresh=useCallback(async()=>{
    setLoading(true);setError('');
    try{
      const session=await localAuthClient().auth.getSession();
      if(session.error)throw session.error;
       const access=session.data.session?.access_token||'';
      setToken(access);
      if(access){setData(await accountApi('/api/saas/me',access));}
      else{setData(null);}
    }catch(e){setError(e instanceof Error?e.message:'Could not load your restaurant dashboard.');}
    finally{setLoading(false);}
  },[]);
  useEffect(()=>{
    const requested=new URLSearchParams(window.location.search).get('tab');
    if(requested==='overview'||requested==='guests'||requested==='promotions'||requested==='analyst')setTab(requested);
    void refresh();
  },[refresh]);

  async function ask(){
    if(!token||!data?.workspace.ai_enabled)return;
    setBusy(true);setError('');setAnswer(null);
    try{setAnswer(await accountApi('/api/saas/analyst',token,'POST',{question}));}
    catch(e){setError(e instanceof Error?e.message:'The analyst is unavailable.');}
    finally{setBusy(false);}
  }

  const w=data?.workspace;
  const s=data?.summary;
  const hasOrders=Boolean(s?.has_connected_source&&s.orders>0);
  const maxDay=Math.max(1,...(s?.daily||[]).map(x=>x.net_sales_minor));

  return <main className="ts9-app">
    <header className="ts9-app-top">
      <div><span className="ts9-kicker">YOUR RESTAURANT · PRIVATE WORKSPACE</span>
        <h1>{w?.name||'Your restaurant'}</h1>
        <p>Understand your guests, spot problems worth investigating, and plan what to do next.</p></div>
      <div className="ts9-app-actions">
        <Link href="/connections" className="ts9-button"><Database size={16}/> Data connections</Link>
        <Link href="/analyst" className="ts9-button secondary">AI analyst <ArrowRight size={16}/></Link>
      </div>
    </header>

    {loading&&<div className="ts9-notice">Loading your private workspace…</div>}
    {error&&<div className="ts9-notice danger" role="alert">{error}</div>}
    {!loading&&!token&&<section className="ts9-empty"><ShieldCheck size={32}/><h2>Sign in to your private workspace</h2><p>The public restaurant demo is available without an account, but this page requires your own login.</p><Link href="/sign-in?next=%2Fdashboard" className="ts9-button primary">Sign in <ArrowRight size={16}/></Link></section>}
    {token&&w&&s&&<>
      <div className="ts9-status-line"><span className="ts9-pill"><Store size={14}/> {w.restaurant_type.replaceAll('_',' ')}</span>
        <span className="ts9-pill"><CreditCard size={14}/> {w.plan==='growth'?'Growth (verified test subscription)':'Local developer / free sandbox'}</span>
        <span className="ts9-pill"><Database size={14}/> {s.has_connected_source?'Square Sandbox connected':'No connected data source'}</span>
        <button className="ts9-text-button" onClick={()=>void refresh()}><RefreshCcw size={14}/> Refresh</button>
      </div>
      {!s.has_connected_source&&<section className="ts9-onboarding-hero">
        <div className="ts9-onboarding-symbol"><Database size={28}/></div>
        <div><span className="ts9-kicker">YOUR NEXT STEP</span><h2>Connect your restaurant before seeing insights.</h2>
          <p>New accounts intentionally start with zero transactions. Connect a Square Sandbox seller to import actual test orders through Square's API and get a dashboard specific to this account.</p>
          <div className="ts9-inline-actions"><Link href="/connections" className="ts9-button primary">Connect Square Sandbox <ArrowRight size={17}/></Link><Link href="/workspace" className="ts9-button secondary">Explore fictional demo</Link></div>
        </div>
      </section>}
      {s.has_connected_source&&!hasOrders&&<section className="ts9-onboarding-hero"><div className="ts9-onboarding-symbol"><Info size={28}/></div><div>
        <h2>Connected, but no completed orders were found.</h2><p>Square Sandbox may not contain completed USD orders in the last 180 days. Create example orders in the Square Sandbox Dashboard or API Explorer, then synchronize again.</p>
        <Link href="/connections" className="ts9-button primary">Review connection <ArrowRight size={16}/></Link>
      </div></section>}
      {hasOrders&&<section className="ts10-card" style={{marginBottom:24,background:'#edf7f1'}}>
        <span className="ts10-eyebrow"><Sparkles size={16}/> YOUR NEXT BUSINESS DECISION</span>
        <h2>What is happening with your guests, and why?</h2>
        <p>You've imported {s.orders} completed orders. Connect the dots with verified sales, identity, and discount evidence. Ask the AI analyst for an explanation, then save a decision to review later.</p>
        <div className="ts10-actions"><Link className="ts10-primary" href="/analyst">Explore AI intelligence <ArrowRight size={16}/></Link><Link className="ts10-secondary" href="/opportunities">Plan an opportunity</Link></div>
      </section>}
      <div className="ts9-tabs" role="tablist" aria-label="Restaurant analytics">
        {([{id:'overview',label:'Overview',icon:BarChart3},{id:'guests',label:'Guests',icon:Users},
          {id:'promotions',label:'Promotions',icon:TicketPercent},{id:'analyst',label:'Ask the analyst',icon:Sparkles}] as const).map(x=><button key={x.id} role="tab" aria-selected={tab===x.id} className={tab===x.id?'active':''} onClick={()=>setTab(x.id)}><x.icon size={16}/>{x.label}</button>)}
      </div>
      {tab==='overview'&&<>
        <div className="ts9-metrics">
          {[{label:'Observed order value¹',value:hasOrders?money(s.net_sales_minor):'—',icon:Wallet},
            {label:'Completed orders',value:hasOrders?count(s.orders):'—',icon:BarChart3},
            {label:'Average order value¹',value:hasOrders?money(s.average_order_minor):'—',icon:TrendingUp},
            {label:'Customer ID coverage',value:hasOrders?`${s.identification_coverage_percent}%`:'—',icon:Users}].map(x=><div className="ts9-metric" key={x.label}><span>{x.label}<x.icon size={17}/></span><strong>{x.value}</strong></div>)}
        </div>
        <div className="ts9-panels">
          <section className="ts9-panel"><div className="ts9-panel-header"><div><span className="ts9-kicker">ORDERS OVER TIME</span><h3>Daily order value¹</h3></div></div>
            {!hasOrders?<p className="ts9-muted">Your order history chart will appear after a successful synchronization.</p>:<div className="ts9-bars" role="img" aria-label="Daily observed order value">
              {s.daily.slice(-28).map(x=><div key={x.date} title={`${x.date}: ${money(x.net_sales_minor)}`}><i style={{height:`${Math.max(3,x.net_sales_minor/maxDay*100)}%`}}/></div>)}
            </div>}
          </section>
          <section className="ts9-panel"><span className="ts9-kicker">LOCATIONS</span><h3>By location</h3>
            {!hasOrders?<p className="ts9-muted">No location data yet.</p>:<div className="ts9-location-list">{s.locations.map(x=><div key={x.location}><div><strong>{x.location.split(':').slice(1).join(':')}</strong><small>{count(x.orders)} orders</small></div><b>{money(x.net_sales_minor)}</b></div>)}</div>}
          </section>
        </div>
      </>}
      {tab==='guests'&&<div className="ts9-panels"><section className="ts9-panel"><span className="ts9-kicker">OBSERVED CUSTOMER BEHAVIOR</span><h3>Guests we can identify</h3>
        <div className="ts9-metrics inner"><div className="ts9-metric"><span>Identified customers</span><strong>{hasOrders?count(s.identified_customers):'—'}</strong></div><div className="ts9-metric"><span>Observed repeat purchasers</span><strong>{hasOrders?count(s.repeat_customers):'—'}</strong></div></div>
        <p className="ts9-muted">Only Square orders with usable customer identifiers count. This is an observed sample, not evidence of retention change. Anonymous orders: {s.anonymous_orders}.</p>
      </section><section className="ts9-panel"><span className="ts9-kicker">DATA QUALITY</span><h3>Identity coverage matters</h3><p>{hasOrders?`${s.identification_coverage_percent}% of orders had a customer ID.`:'We will show identity coverage after synchronization.'}</p><p className="ts9-muted">We cannot determine who comes back from anonymous transactions. No cross-channel identity stitching is performed.</p></section></div>}
      {tab==='promotions'&&<section className="ts9-panel"><span className="ts9-kicker">PROMOTION ECONOMICS</span><h3>Verified campaign data isn't connected yet.</h3>
        <p>Square Sandbox order synchronization imports order and discount totals; it does not yet import verified promotion eligibility, coupon redemptions, or campaign assignments. We won't make up a promotion ROI number.</p>
        {hasOrders&&<p><strong>{money(s.discount_minor)}</strong> in recorded order discounts in the imported sample. This isn't automatically attributable to a specific campaign.</p>}
        <Link href="/workspace" className="ts9-button secondary">Try fictional campaign example <ArrowRight size={15}/></Link>
      </section>}
      {tab==='analyst'&&<section className="ts9-panel ts9-analyst"><span className="ts9-kicker">ACCOUNT ANALYST</span><h3>Ask a question about your connected orders</h3>
        <p>Answers use verified workspace aggregates, not invented restaurant facts.</p>
        {!w.ai_enabled&&<div className="ts9-notice">The private AI analyst requires a verified Growth subscription. You can explore the free evidence-based sample analyst in the public demo. <Link href="/billing">Open test billing</Link>.</div>}
        {!hasOrders&&<div className="ts9-notice">Connect and sync completed Sandbox orders first.</div>}
        <div className="ts9-ask-row"><select aria-label="Choose an analyst question" value={question} onChange={e=>setQuestion(e.target.value)}>{questions.map(x=><option key={x}>{x}</option>)}</select>
          <button className="ts9-button primary" disabled={busy||!w.ai_enabled||!hasOrders} onClick={()=>void ask()}>{busy?'Analyzing…':'Analyze'} <ArrowRight size={16}/></button></div>
        {answer&&<div className="ts9-answer"><p>{answer.answer}</p><small>Evidence: {answer.evidence_keys.join(', ')} · {answer.engine}</small><p><strong>Next step:</strong> {answer.recommended_next_step}</p></div>}
      </section>}
      <p className="ts9-method">¹ Order total excluding separately reported Square tax and tip; payments, refunds, and service charges are not fully reconciled. This is Sandbox test activity, not verified net revenue. <br/>Each account can access only its own workspace records.</p>
    </>}
  </main>
}
