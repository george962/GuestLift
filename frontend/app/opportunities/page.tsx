'use client';
import {useCallback,useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,AlertCircle,CheckCircle2,Lightbulb,RefreshCcw,ShieldCheck,TicketPercent} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

type Opportunity={id:string;title:string;status:string;value:number|null;description:string;evidence:string;action:string};
type Data={workspace:string;has_connected_source:boolean;observed_orders:number;identified_customers:number;reference_basket_minor:number;opportunities:Opportunity[];limitations:string[]};
type OfferType='percent'|'fixed'|'no_offer';
const money=(n:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
export default function Opportunities(){
 const [token,setToken]=useState('');
 const [data,setData]=useState<Data|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');
 const [title,setTitle]=useState('Test a return-visit offer');
 const [objective,setObjective]=useState<'returning_guests'|'discount_review'>('returning_guests');
 const [type,setType]=useState<OfferType>('percent');
 const [value,setValue]=useState(10);
 const [redemptions,setRedemptions]=useState(10);
 const [basket,setBasket]=useState(2500);
 const [margin,setMargin]=useState(35);
 const [notes,setNotes]=useState('');
 const [saving,setSaving]=useState(false);
 const [saved,setSaved]=useState(false);
 const reload=useCallback(async()=>{
  setError('');setLoading(true);
  try{
   const session=await localAuthClient().auth.getSession();
   if(session.error)throw session.error;
   const t=session.data.session?.access_token||'';setToken(t);
   if(t){const result=await accountApi('/api/decisions/opportunities',t) as Data;
    setData(result);setBasket(result.reference_basket_minor);}
  }catch(e){setError(e instanceof Error?e.message:'Unable to load opportunities.');}
  finally{setLoading(false)}
 },[]);
 useEffect(()=>{void reload()},[reload]);
 const discount=useMemo(()=>type==='percent'?Math.floor(basket*value/100):type==='fixed'?Math.min(value,basket):0,[type,value,basket]);
 const expense=discount*redemptions;
 const contribution=Math.floor(basket*redemptions*margin/100)-expense;
 async function save(){if(!token)return;setSaving(true);setError('');
  try{await accountApi('/api/decisions/plans',token,'POST',{
   title,objective,offer_type:type,offer_value:type==='no_offer'?0:value,target_redemptions:redemptions,
   reference_basket_minor:basket,assumed_margin_percent:margin,notes});setSaved(true);
  }catch(e){setError(e instanceof Error?e.message:'Unable to save decision.');}
  finally{setSaving(false)}
 }
 return <main className="ts10-app">
  <div className="ts10-heading"><span className="ts9-kicker">RESTAURANT INTELLIGENCE · DECIDE</span><h1>Know what to act on next.</h1><p>Start with observed guest behavior, evaluate the cost of a possible offer, and save a decision to revisit. All data stays inside your restaurant workspace.</p></div>
  {loading&&<div className="ts10-notice">Checking your connected restaurant data…</div>}
  {error&&<div className="ts10-notice ts10-danger" role="alert"><AlertCircle size={18}/>{error} <button onClick={()=>void reload()}>Retry</button></div>}
  {!loading&&!token&&<div className="ts10-card"><h2>Sign in to review opportunities</h2><p>Your private data isn't shown to visitors.</p><Link className="ts10-primary" href="/sign-in?next=%2Fopportunities">Sign in <ArrowRight size={16}/></Link></div>}
  {token&&data&&<>
    {!data.has_connected_source||!data.observed_orders?<div className="ts10-card"><h2>Connect orders to unlock findings</h2><p>We won't invent a business opportunity for an empty workspace. Connect Square Sandbox and sync completed orders, or explore the public demo.</p><div className="ts10-actions"><Link className="ts10-primary" href="/connections">Connect Square <ArrowRight size={16}/></Link><Link href="/workspace" className="ts10-secondary">Try sample walkthrough</Link></div></div>:<>
      <div className="ts10-summary"><span><strong>{data.observed_orders}</strong> completed orders reviewed</span><span><strong>{data.identified_customers}</strong> identifiable customers</span><span>Reference basket <strong>{money(data.reference_basket_minor)}</strong></span></div>
      <h2 className="ts10-section-heading">What the data can tell us</h2>
      <div className="ts10-opportunities">{data.opportunities.map(o=><section key={o.id} className="ts10-card"><span className="ts10-eyebrow"><Lightbulb size={16}/> {o.status.replaceAll('_',' ')}</span><h3>{o.title}</h3><p>{o.description}</p><p className="ts10-evidence"><ShieldCheck size={15}/> {o.evidence}</p>{o.id!=='identity_coverage'&&<button className="ts10-text-link" onClick={()=>{setObjective(o.id as 'returning_guests'|'discount_review');setTitle(o.id==='discount_review'?'Evaluate a discount-cost experiment':'Test a return-visit offer');document.getElementById('compare-offers')?.scrollIntoView({behavior:'smooth'});}}>{o.action} <ArrowRight size={16}/></button>}{o.id==='identity_coverage'&&<Link className="ts10-text-link" href="/dashboard?tab=guests">Review guest evidence <ArrowRight size={16}/></Link>}</section>)}</div>
      <section className="ts10-card ts10-comparison" id="compare-offers"><span className="ts10-eyebrow"><TicketPercent size={16}/> STEP 2 · COMPARE A SCENARIO</span><h2>What would an offer cost?</h2><p>Choose a hypothetical number of purchases and a discount. This models expenses and contribution <strong>if those purchases occurred</strong>. It does not forecast response, calculate lift, or send a promotion.</p>
        <div className="ts10-form-grid"><label>Decision title<input value={title} onChange={e=>{setTitle(e.target.value);setSaved(false)}} minLength={3} maxLength={140}/></label><label>Business objective<select value={objective} onChange={e=>{setObjective(e.target.value as typeof objective);setSaved(false)}}><option value="returning_guests">Understand returning guests</option><option value="discount_review">Review discount economics</option></select></label>
         <label>Offer type<select value={type} onChange={e=>{const v=e.target.value as OfferType;setType(v);setValue(v==='fixed'?1000:v==='percent'?10:0);setSaved(false)}}><option value="percent">Percent off</option><option value="fixed">Fixed amount off</option><option value="no_offer">No discount (baseline)</option></select></label>
         {type!=='no_offer'&&<label>{type==='percent'?'Percent off (%)':'Fixed discount (cents)'}<input type="number" min={type==='percent'?1:1} max={type==='percent'?80:basket} value={value} onChange={e=>{setValue(Number(e.target.value));setSaved(false)}}/></label>}
         <label>Assumed completed purchases<input type="number" min="1" max="10000" value={redemptions} onChange={e=>{setRedemptions(Number(e.target.value));setSaved(false)}}/></label>
         <label>Assumed basket size (cents)<input type="number" min="100" max="1000000" value={basket} onChange={e=>{setBasket(Number(e.target.value));setSaved(false)}}/></label>
         <label>Assumed pre-discount contribution margin (%)<input type="number" min="1" max="95" value={margin} onChange={e=>{setMargin(Number(e.target.value));setSaved(false)}}/></label>
         <label className="ts10-full">Notes / what you want to learn<textarea rows={3} maxLength={1200} value={notes} onChange={e=>{setNotes(e.target.value);setSaved(false)}} placeholder="Example: Compare the cost of a 10% offer with a $10 offer before running a controlled test."/></label>
        </div>
        <div className="ts10-scenario-results"><div><span>Discount per hypothetical order</span><strong>{money(discount)}</strong></div><div><span>Total modeled discount expense</span><strong>{money(expense)}</strong></div><div><span>Modeled contribution after discounts*</span><strong>{money(contribution)}</strong></div></div>
        <p className="ts10-small">*Assumes {redemptions.toLocaleString()} purchases at {money(basket)} each, with {margin}% pre-discount contribution. <strong>Not incremental profit.</strong> No customer targeting, consent or send action is implemented.</p>
        {saved?<div className="ts10-notice ts10-success" role="status"><CheckCircle2 size={18}/> Draft saved. <Link href="/experiments">Review your saved decisions <ArrowRight size={15}/></Link></div>:<button className="ts10-primary" disabled={saving||!title.trim()||redemptions<1||basket<100||margin<1||margin>95} onClick={()=>void save()}>{saving?'Saving draft…':'Save experiment draft'} <ArrowRight size={16}/></button>}
      </section>
    </>}
    <div className="ts10-notice"><ShieldCheck size={18}/> Test-only: Square Sandbox data, no live marketing, no customer exports, and no claims of causal impact.</div>
  </>}
 </main>
}
