'use client';

import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,CheckCircle2,CreditCard,RefreshCcw,ShieldCheck,LockKeyhole,ExternalLink,AlertCircle,Clock3} from 'lucide-react';
import {accountApi,apiOrigin,localAuthClient} from '@/lib/local-auth';

type Workspace = {
  plan:string;
  subscription_status:string;
  name:string;
  ai_enabled:boolean;
  has_billing_customer:boolean;
};
type Configuration = {
  auth_configured:boolean;
  test_checkout_configured:boolean;
  test_webhook_configured:boolean;
  live_payments_enabled:boolean;
  real_merchant_data_allowed:boolean;
};
type ReconcileResult = {
  verified:boolean;
  pending?:boolean;
  message?:string;
  workspace:Workspace;
  access_granted?:boolean;
};

export default function Billing() {
  const [token,setToken]=useState('');
  const [account,setAccount]=useState<Workspace|null>(null);
  const [config,setConfig]=useState<Configuration|null>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [repairing,setRepairing]=useState(false);
  const [message,setMessage]=useState('');
  const [feedback,setFeedback]=useState<'success'|'warning'|'error'|null>(null);

  const refresh=useCallback(async (t:string)=>{
    const response=await accountApi('/api/saas/me',t);
    setAccount(response.workspace as Workspace);
    return response.workspace as Workspace;
  },[]);

  const reconcile=useCallback(async (t:string, sessionId?:string)=>{
    const result=await accountApi('/api/saas/billing/reconcile',t,'POST',
      sessionId?{session_id:sessionId}:{} ) as ReconcileResult;
    setAccount(result.workspace);
    if(result.access_granted){
      setFeedback('success');
      setMessage('Stripe verified your Growth subscription. Your test plan is now active.');
    }else{
      setFeedback('warning');
      setMessage(result.message||`Stripe verified the subscription, but the current status is ${result.workspace.subscription_status}. Paid access is not yet active.`);
    }
    return result;
  },[]);

  useEffect(()=>{
    let active=true;
    void fetch(apiOrigin()+'/api/saas/config',{cache:'no-store'})
      .then(r=>r.ok?r.json():null)
      .then(data=>{if(active)setConfig(data)})
      .catch(()=>{});
    void localAuthClient().auth.getSession().then(async({data})=>{
      if(!active)return;
      const t=data.session?.access_token||'';
      setToken(t);
      if(!t){setLoading(false);return;}
      try{
        await refresh(t);
        if(!active)return;
        const checkout=new URLSearchParams(window.location.search).get('checkout');
        if(checkout==='return'){
          // v0.9's legacy success URL did not contain a session ID.
          setRepairing(true);
          try{await reconcile(t)}
          catch(e){
            if(active){setFeedback('warning');setMessage(
              (e instanceof Error?e.message:'Could not check Stripe.')+
              ' You can retry using Find my completed checkout. Do not pay again.');}
          }finally{if(active)setRepairing(false)}
        }else if(checkout==='canceled'){
          setFeedback('warning');setMessage('Checkout was canceled. No new subscription was activated.');
        }
      }catch(e){if(active){setFeedback('error');setMessage(e instanceof Error?e.message:'Could not load billing status.')}}
      finally{if(active)setLoading(false)}
    });
    return()=>{active=false};
  },[refresh,reconcile]);

  async function action(type:'checkout'|'portal'){
    if(!token){setFeedback('error');setMessage('Sign in before managing billing.');return;}
    setBusy(true);setMessage('');setFeedback(null);
    try{
      const result=await accountApi('/api/saas/billing/'+type,token,'POST');
      if(typeof result.url==='string'&&result.url.startsWith('https://')){
        window.location.assign(result.url);
      }else{
        throw new Error('Stripe did not return a secure checkout URL.');
      }
    }catch(e){setFeedback('error');setMessage(e instanceof Error?e.message:'Billing request failed.');}
    finally{setBusy(false)}
  }
  async function repair(){
    if(!token)return;
    setRepairing(true);setFeedback(null);setMessage('');
    try{await reconcile(token)}
    catch(e){setFeedback('warning');setMessage(
      (e instanceof Error?e.message:'Unable to reconcile checkout.')+
      ' Check Stripe CLI webhook responses. Do not start another purchase until this is resolved.');}
    finally{setRepairing(false)}
  }
  async function checkStatus(){
    if(!token)return;
    setBusy(true);
    try{await refresh(token);setFeedback('success');setMessage('Account status refreshed from the database.');}
    catch(e){setFeedback('error');setMessage(e instanceof Error?e.message:'Unable to refresh account status.');}
    finally{setBusy(false)}
  }

  const active=account?.plan==='growth'&&['active','trialing'].includes(account.subscription_status);
  const canCheckout=Boolean(config?.test_checkout_configured);
  const hasCustomer=Boolean(account?.has_billing_customer);

  return <main className="ts-public-page v7-billing-page ts10-billing">
    <div className="ts-page-hero">
      <span className="ts-kicker">YOUR ACCOUNT · BILLING</span>
      <h1>Your subscription.</h1>
      <p>Manage your verified test subscription. Payment details and cancellations are handled securely by Stripe.</p>
    </div>
    <div className="v7-billing-layout">
      <section className="ts-settings-card v7-billing-main">
        <div className="ts-section-icon"><CreditCard size={25}/></div>
        {!token&&!loading ? <>
          <span className="ts-kicker">ACCOUNT REQUIRED</span>
          <h2>Sign in to manage your plan.</h2>
          <p>Your subscription is linked to your verified local TableSignal account.</p>
          <div className="v7-billing-buttons">
            <Link className="ts-btn-dark" href="/sign-in?next=%2Fbilling">Sign in <ArrowRight size={17}/></Link>
            <Link className="ts-btn-outline" href="/sign-up?next=%2Fbilling">Create account</Link>
          </div>
        </> : <>
          <span className="ts-kicker">SERVER-VERIFIED ACCOUNT STATUS</span>
          <h2>{loading?'Checking your plan…':active?'Growth plan':'Sandbox plan'}</h2>
          <div className="ts-plan-status"><span>Restaurant</span><strong>{account?.name||'Your workspace'}</strong></div>
          <div className="ts-plan-status"><span>Subscription</span><strong>{account?.subscription_status||'none'}</strong></div>
          <div className="ts-plan-status"><span>Account AI analyst</span><strong>{account?.ai_enabled?'Enabled (once data is connected)':'Not enabled'}</strong></div>
          {active&&<div className="ts-alert good" role="status"><CheckCircle2 size={18}/> Your Stripe test subscription is verified. You can now connect a Square Sandbox data source and use the private analyst.</div>}
          {message&&<div className={'ts-alert'+(feedback==='success'?' good':feedback==='error'?' error':'')} role="status">
            {feedback==='success'?<CheckCircle2 size={18}/>:feedback==='error'?<AlertCircle size={18}/>:<Clock3 size={18}/>}
            {message}
          </div>}
          <div className="v7-billing-buttons">
            {!active&&<button type="button" className="ts-btn-dark" disabled={!token||busy||loading||repairing||!canCheckout} onClick={()=>void action('checkout')}>
              Start Growth test checkout <ExternalLink size={16}/>
            </button>}
            {hasCustomer&&<button type="button" className="ts-btn-dark" disabled={!token||busy||loading||repairing} onClick={()=>void action('portal')}>
              Manage my Stripe subscription <ExternalLink size={16}/>
            </button>}
            {!active&&canCheckout&&<button type="button" className="ts-mini-button" disabled={!token||busy||loading||repairing} onClick={()=>void repair()}>
              <RefreshCcw size={15}/> {repairing?'Checking Stripe…':'Find my completed test checkout'}
            </button>}
            <button type="button" className="ts-mini-button" disabled={!token||busy||loading||repairing} onClick={()=>void checkStatus()}>
              <RefreshCcw size={15}/> Refresh plan status
            </button>
          </div>
          {!canCheckout&&<div className="ts-alert">Stripe test Checkout is not configured on the backend. Add the sandbox secret and recurring Price ID in your local .env.</div>}
          {active&&<p style={{marginTop:18}}><Link href="/connections">Connect Square Sandbox <ArrowRight size={16}/></Link></p>}
          {!active&&<div className="ts10-notice" style={{marginTop:18}}>Already completed a test purchase? Use “Find my completed test checkout” first. You should not pay twice.</div>}
        </>}
      </section>
      <aside className="v7-billing-aside">
        <div className="v7-billing-feature"><LockKeyhole size={21}/><strong>Account security</strong><p>Your local account owns its own subscription and restaurant workspace.</p></div>
        <div className="v7-billing-feature"><ShieldCheck size={21}/><strong>Checkout verification</strong><p>Checkout returns are checked against Stripe's API. The account must match the verified subscription and Growth price.</p></div>
        <div className="v7-billing-feature"><CheckCircle2 size={21}/><strong>Subscription management</strong><p>Manage a linked subscription through Stripe's customer portal.</p></div>
        <div className="v7-billing-feature caution"><CreditCard size={21}/><strong>No live billing</strong><p>Actual charges and real merchant onboarding remain disabled.</p></div>
      </aside>
    </div>
    <div className="ts-caution"><ShieldCheck size={21}/><p>Growth access requires an authenticated account and a server-verified Stripe test subscription. If webhook delivery is interrupted, a completed Checkout can be reconciled securely without paying again.</p></div>
  </main>;
}
