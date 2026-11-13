'use client';
import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {ArrowRight,CheckCircle2,CreditCard,Database,ShieldCheck,Store} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';
type Step=1|2|3;
type Choice='not_chosen'|'sandbox'|'growth';
export default function Onboarding(){
 const router=useRouter();
 const [step,setStep]=useState<Step>(1);const [token,setToken]=useState('');
 const [checked,setChecked]=useState(false);const [name,setName]=useState('');
 const [kind,setKind]=useState('fast_casual');const [goal,setGoal]=useState('customer_retention');
 const [choice,setChoice]=useState<Choice>('not_chosen');
 const [busy,setBusy]=useState(false);const [notice,setNotice]=useState('');
 const load=useCallback(async()=>{
  try{
   const session=await localAuthClient().auth.getSession();
   if(session.error)throw session.error;
   const t=session.data.session?.access_token||'';setToken(t);
   if(t){const [account,progress]=await Promise.all([accountApi('/api/saas/me',t),accountApi('/api/saas/onboarding',t)]);
    if(account.workspace.name!=='My Restaurant')setName(account.workspace.name);
    if(account.workspace.restaurant_type)setKind(account.workspace.restaurant_type);
    if(account.workspace.goal)setGoal(account.workspace.goal);
    setChoice(progress.plan_choice);
    setStep(progress.stage as Step);
    if(account.summary?.has_connected_source)setStep(3);
   }
  }catch(e){setNotice(e instanceof Error?`Unable to check your account: ${e.message}`:'Unable to load onboarding.');}
  finally{setChecked(true)}
 },[]);
 useEffect(()=>{void load()},[load]);
 async function saveProfile(){if(!token)return;setBusy(true);setNotice('');
  try{await accountApi('/api/saas/profile',token,'POST',{name:name.trim(),restaurant_type:kind,goal});
    setStep(2);setNotice('Restaurant profile saved. Choose your development plan next.');}
  catch(e){setNotice(e instanceof Error?e.message:'Unable to save your restaurant.');}
  finally{setBusy(false)}
 }
 async function selectPlan(which:'sandbox'|'growth'){
  if(!token)return;setBusy(true);setNotice('');
  try{await accountApi('/api/saas/onboarding',token,'POST',{stage:3,plan_choice:which});
   setChoice(which);setStep(3);
   if(which==='growth')router.push('/billing');
   else setNotice('Sandbox selected. You can now connect Square test data.');
  }catch(e){setNotice(e instanceof Error?e.message:'Could not save your plan choice.');}
  finally{setBusy(false)}
 }
 return <main className="ts10-app">
  <div className="ts10-heading"><span className="ts9-kicker">YOUR RESTAURANT · GET STARTED</span><h1>Let's make TableSignal yours.</h1><p>Three steps to your private workspace. You can leave and come back—we save your setup progress in the database.</p></div>
  <div className="ts9-onboarding-steps" style={{marginBottom:25}}><div className={step===1?'current':'done'}><Store size={17}/> 1 · Restaurant</div><div className={step===2?'current':step>2?'done':''}><CreditCard size={17}/> 2 · Plan</div><div className={step===3?'current':''}><Database size={17}/> 3 · Connect data</div></div>
  {!checked&&<div className="ts10-notice">Loading your saved setup…</div>}
  {notice&&<div className="ts10-notice" role="status">{notice} <button onClick={()=>void load()}>Refresh</button></div>}
  {checked&&!token&&<section className="ts10-card"><h2>Sign in to start</h2><p>Your restaurant's data belongs to your account.</p><div className="ts10-actions"><Link className="ts10-primary" href="/sign-in?next=%2Fonboarding">Sign in <ArrowRight size={16}/></Link><Link className="ts10-secondary" href="/sign-up?next=%2Fonboarding">Create account</Link></div></section>}
  {token&&step===1&&<section className="ts10-card"><span className="ts10-eyebrow">STEP 1 · RESTAURANT PROFILE</span><h2>What should we call your restaurant?</h2><div className="ts10-form-grid"><label>Restaurant name<input minLength={2} maxLength={120} required value={name} placeholder="e.g. Harbor Café" onChange={e=>setName(e.target.value)}/></label><label>Restaurant type<select value={kind} onChange={e=>setKind(e.target.value)}><option value="fast_casual">Quick service / fast casual</option><option value="full_service">Full service</option><option value="cafe">Cafe / coffee</option><option value="other">Other</option></select></label><label>What do you want to improve?<select value={goal} onChange={e=>setGoal(e.target.value)}><option value="customer_retention">Guest return visits</option><option value="promotion_profit">Promotion economics</option><option value="sales_visibility">Sales visibility</option></select></label></div><button className="ts10-primary" disabled={busy||name.trim().length<2} onClick={()=>void saveProfile()}>{busy?'Saving…':'Save and continue'} <ArrowRight size={16}/></button></section>}
  {token&&step===2&&<section className="ts10-card"><span className="ts10-eyebrow">STEP 2 · CHOOSE AN EXPERIENCE</span><h2>How would you like to start?</h2><p>Both options use fictional Square Sandbox data in this local developer release. Live payments and real merchant data aren't enabled.</p><div className="ts10-opportunities" style={{gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))'}}><div className="ts10-card"><h3>Free Sandbox</h3><p>Connect your own Square test seller, explore verified aggregate metrics, and save hypothetical promotion plans.</p><button className="ts10-secondary" disabled={busy} onClick={()=>void selectPlan('sandbox')}>Continue free <ArrowRight size={16}/></button></div><div className="ts10-card"><h3>Growth · Stripe test</h3><p>Try the proposed $149/month plan with Stripe's Sandbox. Your real bank account won't be charged.</p><button className="ts10-primary" disabled={busy} onClick={()=>void selectPlan('growth')}>Try test checkout <ArrowRight size={16}/></button></div></div></section>}
  {token&&step===3&&<section className="ts10-card"><span className="ts10-eyebrow"><CheckCircle2 size={16}/> YOUR SETUP PROGRESS IS SAVED</span><h2>Next: connect your orders.</h2><p>Restaurant: <strong>{name}</strong> · Chosen path: <strong>{choice==='growth'?'Growth test subscription':'Free Sandbox'}</strong>. You can connect a Square Sandbox seller, import simulated orders and start investigating business decisions.</p><div className="ts10-actions"><Link href="/connections" className="ts10-primary">Connect Square Sandbox <ArrowRight size={16}/></Link><Link href="/dashboard" className="ts10-secondary">Go to my overview</Link><Link href="/billing" className="ts10-secondary">Review billing</Link></div></section>}
  <div className="ts10-notice"><ShieldCheck size={18}/> Local development only. This application does not accept live POS data or real payments.</div>
 </main>
}
