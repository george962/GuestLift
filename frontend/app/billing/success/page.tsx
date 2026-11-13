'use client';

import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,CheckCircle2,Clock3,ShieldCheck,AlertCircle,RefreshCcw,Store} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

type Verified = {verified:boolean;pending?:boolean;access_granted?:boolean;
  workspace?:{name:string;subscription_status:string;plan:string};message?:string};

export default function BillingSuccess(){
  const [state,setState]=useState<'checking'|'active'|'pending'|'error'|'sign-in'>('checking');
  const [result,setResult]=useState<Verified|null>(null);
  const [message,setMessage]=useState('');
  const [retrying,setRetrying]=useState(false);

  const check=useCallback(async()=>{
    const sessionId=new URLSearchParams(window.location.search).get('session_id');
    if(!sessionId||!/^cs_test_[A-Za-z0-9_]+$/.test(sessionId)){
      setState('error');setMessage('The checkout return is missing a valid Stripe test session ID. Open Billing and use Find my completed test checkout.');return;
    }
    const {data}=await localAuthClient().auth.getSession();
    const token=data.session?.access_token;
    if(!token){setState('sign-in');return;}
    try{
      const response=await accountApi('/api/saas/billing/reconcile',token,'POST',{session_id:sessionId}) as Verified;
      setResult(response);
      if(response.access_granted){setState('active');setMessage('Your Growth plan has been verified and activated.');}
      else{setState('pending');setMessage(response.message||'Stripe has not confirmed an active subscription yet.');}
    }catch(e){setState('error');setMessage(e instanceof Error?e.message:'Unable to verify the subscription.');}
  },[]);

  useEffect(()=>{void check()},[check]);
  async function retry(){setRetrying(true);setState('checking');await check();setRetrying(false)}

  const active=state==='active';
  return <main className="ts-public-page v7-billing-page">
    <div className="ts-page-hero ts-centered">
      <span className="ts-kicker">TABLESIGNAL · STRIPE SANDBOX</span>
      <h1>{active?'Your Growth plan is ready.':state==='checking'?'Verifying your subscription…':
         state==='sign-in'?'Sign in to verify your checkout.':state==='pending'?'Your payment is processing.':'We couldn’t verify this checkout.'}</h1>
      <p>{active?'Stripe confirmed the account, price, and current subscription status.':
          'We verify this purchase directly with Stripe before enabling paid access. Your return to this page alone is not proof of payment.'}</p>
    </div>
    <div className="ts-settings-card" style={{maxWidth:740,margin:'0 auto 64px',padding:'36px 42px'}}>
      <div className="ts-section-icon">{active?<CheckCircle2 size={26}/>:state==='error'?<AlertCircle size={26}/>:<Clock3 size={26}/>}</div>
      <span className="ts-kicker">PAYMENT CONFIRMATION · TEST MODE</span>
      <h2>{active?'Subscription verified':state==='pending'?'Confirmation pending':state==='checking'?'Contacting Stripe…':state==='sign-in'?'Account verification required':'Verification needs attention'}</h2>
      {result?.workspace&&<>
        <div className="ts-plan-status"><span>Restaurant</span><strong>{result.workspace.name}</strong></div>
        <div className="ts-plan-status"><span>Plan</span><strong>{result.workspace.plan==='growth'?'Growth':'Sandbox'}</strong></div>
        <div className="ts-plan-status"><span>Subscription status</span><strong>{result.workspace.subscription_status}</strong></div>
      </>}
      {message&&<div className={'ts-alert'+(active?' good':state==='error'?' error':'')} role="status">{message}</div>}
      {state==='sign-in'&&<p><Link className="ts-btn-dark" href="/sign-in?next=%2Fbilling">Sign in to billing <ArrowRight size={17}/></Link></p>}
      <div className="v7-billing-buttons" style={{marginTop:24}}>
        {active?<>
          <Link className="ts-btn-dark" href="/connections"><Store size={18}/> Connect Square Sandbox <ArrowRight size={17}/></Link>
          <Link className="ts-btn-outline" href="/dashboard">My restaurant dashboard</Link>
        </>:<>
          {(state==='pending'||state==='error')&&<button type="button" className="ts-btn-dark" onClick={()=>void retry()} disabled={retrying}>
            <RefreshCcw size={17}/> {retrying?'Verifying…':'Verify with Stripe again'}
          </button>}
          <Link className="ts-btn-outline" href="/billing">Go to billing</Link>
        </>}
      </div>
      <div className="ts-auth-disclaimer" style={{marginTop:22}}><ShieldCheck size={16}/> This is a Stripe Sandbox transaction. No real funds were charged. Do not repeat the payment while verification is pending.</div>
    </div>
  </main>;
}
