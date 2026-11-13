'use client';

import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight, CheckCircle2, CreditCard, Database, ShieldCheck, Store} from 'lucide-react';
import {accountApi, apiOrigin, localAuthClient} from '@/lib/local-auth';

type Step=1|2|3;
type Config={test_checkout_configured:boolean;test_webhook_configured:boolean;live_payments_enabled:boolean};

export default function Onboarding(){
  const [step,setStep]=useState<Step>(1);
  const [signedIn,setSignedIn]=useState(false);
  const [token,setToken]=useState('');
  const [name,setName]=useState('');
  const [kind,setKind]=useState('fast_casual');
  const [goal,setGoal]=useState('customer_retention');
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState('');
  const [config,setConfig]=useState<Config|null>(null);
  useEffect(()=>{
    let mounted=true;
    void localAuthClient().auth.getSession().then(async({data})=>{
      if(!mounted)return;
      const t=data.session?.access_token||'';setToken(t);setSignedIn(Boolean(t));
      if(t){try{
        const r=await accountApi('/api/saas/me',t);
        if(mounted&&r.workspace.name!=='My Restaurant')setName(r.workspace.name);
      }catch{/* Start with empty profile fields. */}}
    });
    void fetch(apiOrigin()+'/api/saas/config',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(v=>{if(mounted)setConfig(v)}).catch(()=>{});
    return()=>{mounted=false};
  },[]);
  async function save(){
    if(!token){setNotice('Sign in first to save your restaurant.');return;}
    if(name.trim().length<2){setNotice('Enter a restaurant name with at least two characters.');return;}
    setBusy(true);setNotice('');
    try{await accountApi('/api/saas/profile',token,'POST',{name:name.trim(),restaurant_type:kind,goal});setStep(2)}
    catch(e){setNotice(e instanceof Error?e.message:'Unable to save your restaurant.');}
    finally{setBusy(false)}
  }
  return <main className="ts9-app">
    <header className="ts9-app-top"><div><span className="ts9-kicker">YOUR ACCOUNT · SETUP</span><h1>Make TableSignal yours.</h1>
      <p>Set up your restaurant, choose a development plan, then connect a source of data. No generic sample totals will appear in your private dashboard.</p></div></header>
    <div className="ts9-onboarding-steps">
      <div className={step===1?'current':'done'}><Store size={17}/> 1 · Restaurant</div>
      <div className={step===2?'current':step===3?'done':''}><CreditCard size={17}/> 2 · Choose plan</div>
      <div className={step===3?'current':''}><Database size={17}/> 3 · Data connection</div>
    </div>
    {!signedIn&&<section className="ts9-empty"><ShieldCheck size={31}/><h2>Start by creating your account.</h2>
      <p>Only signed-in accounts can own private restaurant data or request Sandbox connections.</p>
      <Link className="ts9-button primary" href="/sign-up?next=%2Fonboarding">Create account <ArrowRight size={16}/></Link>
      <Link className="ts9-button secondary" href="/sign-in?next=%2Fonboarding">Already have an account?</Link>
    </section>}
    {signedIn&&step===1&&<section className="ts9-panel ts9-setup-card"><span className="ts9-kicker">01 · RESTAURANT PROFILE</span><h3>Tell us about your business.</h3>
      <p>We use this context to organize your dashboard and future analyst questions.</p>
      <div className="ts-form"><label>Restaurant or group name<input value={name} onChange={e=>setName(e.target.value)} maxLength={120} minLength={2} placeholder="e.g. Harbor Café" required /></label>
        <label>Business type<select value={kind} onChange={e=>setKind(e.target.value)}><option value="fast_casual">Quick service / fast casual</option><option value="full_service">Full service</option><option value="cafe">Cafe / coffee</option><option value="other">Other</option></select></label>
        <label>What matters most?<select value={goal} onChange={e=>setGoal(e.target.value)}><option value="customer_retention">Returning customers</option><option value="promotion_profit">Promotion spending</option><option value="sales_visibility">Sales and location visibility</option></select></label>
        <button className="ts9-button primary" disabled={busy} onClick={()=>void save()}>{busy?'Saving…':'Save restaurant'} <ArrowRight size={16}/></button>
      </div>
    </section>}
    {signedIn&&step===2&&<section className="ts9-panel ts9-setup-card"><span className="ts9-kicker">02 · CHOOSE YOUR EXPERIENCE</span><h3>Explore free—or test the future paid plan.</h3>
      <div className="ts9-setup-plans">
        <div><span className="ts9-kicker">DEVELOPMENT SANDBOX</span><h3>Free to test</h3><p>Your private account can sync your own Square Sandbox test seller using local developer credentials. Private model-backed AI remains locked.</p>
          <button className="ts9-button secondary" onClick={()=>setStep(3)}>Continue with Sandbox <ArrowRight size={16}/></button></div>
        <div><span className="ts9-kicker">GROWTH · TEST MODE</span><h3>$149 / location / month</h3><p>Proposed future pricing. Stripe test checkout does not charge real money. Paid AI is enabled only by verified subscription webhooks.</p>
          <Link className="ts9-button primary" href="/billing">Go to Stripe test billing <ArrowRight size={16}/></Link>
          {!config?.test_checkout_configured&&<small>Stripe test keys are not configured. You can continue with the free developer Sandbox.</small>}
        </div>
      </div>
    </section>}
    {signedIn&&step===3&&<section className="ts9-panel ts9-setup-card"><span className="ts9-kicker">03 · YOUR DATA SOURCE</span><h3>Connect Square Sandbox.</h3>
      <p>Once connected, TableSignal will fetch the Sandbox seller's completed orders using Square's actual APIs. Your personal dashboard starts empty and only shows records imported for your account.</p>
      <div className="ts9-inline-actions"><Link href="/connections" className="ts9-button primary">Connect my Sandbox <ArrowRight size={17}/></Link>
        <Link href="/dashboard" className="ts9-button secondary">Open empty dashboard</Link></div>
    </section>}
    {notice&&<div role="status" className="ts9-notice danger">{notice}</div>}
    <div className="ts9-important"><ShieldCheck size={20}/><p>This is a local development service. Customer verification emails, production Stripe payments, live Square merchants, and real customer files are disabled. The free public demo uses fictional data only.</p></div>
  </main>
}
