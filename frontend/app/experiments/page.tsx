'use client';
import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,CheckCircle2,ClipboardList,RefreshCcw,ShieldCheck} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';
type Plan={id:string;title:string;objective:string;offer_type:string;offer_value:number;target_redemptions:number;
 reference_basket_minor:number;assumed_margin_percent:number;discount_budget_minor:number;modeled_contribution_minor:number;
 status:string;notes:string;created_at:string;updated_at:string};
const money=(n:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
export default function Experiments(){
 const [token,setToken]=useState('');const [plans,setPlans]=useState<Plan[]>([]);
 const [loading,setLoading]=useState(true);const [error,setError]=useState('');
 const [working,setWorking]=useState('');const [notice,setNotice]=useState('');
 const load=useCallback(async()=>{
  setLoading(true);setError('');
  try{const s=await localAuthClient().auth.getSession();if(s.error)throw s.error;
   const t=s.data.session?.access_token||'';setToken(t);
   if(t){const r=await accountApi('/api/decisions/plans',t);setPlans(r.plans||[])}
  }catch(e){setError(e instanceof Error?e.message:'Could not retrieve your saved plans')}
  finally{setLoading(false)}
 },[]);
 useEffect(()=>{void load()},[load]);
 async function update(id:string,status:string){if(!token)return;setWorking(id);setNotice('');
  try{await accountApi('/api/decisions/plans/'+id+'/status',token,'POST',{status});
      setNotice('Tracking status saved. No customer messages or campaigns were sent.');await load();}
  catch(e){setError(e instanceof Error?e.message:'Could not update status')}finally{setWorking('')}
 }
 return <main className="ts10-app"><div className="ts10-heading"><span className="ts9-kicker">RESTAURANT INTELLIGENCE · FOLLOW THROUGH</span><h1>Your saved experiments.</h1><p>Keep assumptions and decisions in one place. Change tracking status as you review them; TableSignal does not launch campaigns automatically.</p></div>
  {loading&&<div className="ts10-notice">Loading saved decisions…</div>}
  {error&&<div className="ts10-notice ts10-danger" role="alert">{error}<button onClick={()=>void load()}>Retry</button></div>}
  {!loading&&!token&&<div className="ts10-card"><h2>Sign in to your restaurant</h2><Link className="ts10-primary" href="/sign-in?next=%2Fexperiments">Sign in <ArrowRight size={16}/></Link></div>}
  {!loading&&token&&!plans.length&&<div className="ts10-card ts10-empty"><ClipboardList size={34}/><h2>No decisions saved yet</h2><p>Review your restaurant's order patterns, compare hypothetical promotion costs and save your first experiment draft.</p><Link href="/opportunities" className="ts10-primary">Explore opportunities <ArrowRight size={16}/></Link></div>}
  {notice&&<div className="ts10-notice ts10-success" role="status"><CheckCircle2 size={18}/>{notice}</div>}
  <div className="ts10-plan-list">{plans.map(p=><article key={p.id} className="ts10-card"><div className="ts10-plan-header"><div><span className="ts10-eyebrow">{p.objective.replaceAll('_',' ')} · {new Date(p.created_at).toLocaleDateString()}</span><h2>{p.title}</h2></div><span className="ts10-status">{p.status}</span></div>
   <div className="ts10-plan-facts"><span><small>Offer</small><strong>{p.offer_type==='percent'?`${p.offer_value}% off`:p.offer_type==='fixed'?`${money(p.offer_value)} off`:'No incentive'}</strong></span><span><small>Hypothetical orders</small><strong>{p.target_redemptions}</strong></span><span><small>Modeled discount budget</small><strong>{money(p.discount_budget_minor)}</strong></span><span><small>Modeled contribution*</small><strong>{money(p.modeled_contribution_minor)}</strong></span></div>
   {p.notes&&<p>{p.notes}</p>}<p className="ts10-small">*Scenario only. Assumed {p.assumed_margin_percent}% pre-discount contribution margin. This is neither incremental profit nor evidence of marketing effectiveness.</p>
   <div className="ts10-actions"><label>Tracking status <select aria-label={`Status for ${p.title}`} disabled={working===p.id} value={p.status} onChange={e=>void update(p.id,e.target.value)}><option value="draft">Draft</option><option value="planned">Planned (not sent)</option><option value="reviewed">Reviewed</option></select></label></div>
  </article>)}</div>
  <div className="ts10-actions"><Link className="ts10-primary" href="/opportunities">Plan another decision <ArrowRight size={16}/></Link><Link className="ts10-secondary" href="/dashboard">Back to restaurant overview</Link></div>
  <div className="ts10-notice"><ShieldCheck size={18}/> Everything here is a local, account-scoped planning draft. No live campaigns, real customer data, or customer communications.</div>
 </main>
}
