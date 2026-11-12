'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,CheckCircle2,CreditCard,RefreshCcw,ShieldCheck,LockKeyhole,ExternalLink} from 'lucide-react';
import {accountApi,apiOrigin,localAuthClient} from '@/lib/local-auth';
type State={plan:string;subscription_status:string;name:string;ai_enabled:boolean};
type Configuration={auth_configured:boolean;test_checkout_configured:boolean;test_webhook_configured:boolean;live_payments_enabled:boolean;real_merchant_data_allowed:boolean};
export default function Billing(){
 const sb=localAuthClient();const [token,setToken]=useState(''),[state,setState]=useState<State|null>(null),[config,setConfig]=useState<Configuration|null>(null);
 const [busy,setBusy]=useState(false),[loading,setLoading]=useState(true),[message,setMessage]=useState('');
 async function refresh(t=token){if(!t){setLoading(false);return}try{const r=await accountApi('/api/saas/me',t);setState(r.workspace);setMessage('')}catch(e){setMessage(e instanceof Error?e.message:'Could not load subscription')}finally{setLoading(false)}}
 useEffect(()=>{let active=true;
  void fetch(apiOrigin()+'/api/saas/config',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(c=>{if(active)setConfig(c)}).catch(()=>{});
  if(!sb){setLoading(false);return}
  void sb.auth.getSession().then(({data})=>{if(!active)return;const t=data.session?.access_token;if(t){setToken(t);void refresh(t)}else setLoading(false)});
  const {data:listener}=sb.auth.onAuthStateChange((_event,s)=>{if(!active)return;const t=s?.access_token||'';setToken(t);if(!t){setState(null);setLoading(false)} });
  return()=>{active=false;listener.subscription.unsubscribe()};
 },[sb]);
 async function action(type:'checkout'|'portal'){
  if(!token){setMessage('Please sign in before managing billing.');return}
  setBusy(true);setMessage('');try{
   const r=await accountApi('/api/saas/billing/'+type,token,'POST');
   if(r.url && /^https:\/\//.test(r.url))window.location.assign(r.url);else setMessage('Stripe did not return a valid secure checkout URL.');
  }catch(e){setMessage(e instanceof Error?e.message:'Billing request failed.')}finally{setBusy(false)}
 }
 const isGrowth=state?.plan==='growth'&&['active','trialing'].includes(state.subscription_status);
 const canCheckout=Boolean(config?.test_checkout_configured);
 return <main className="ts-public-page v7-billing-page">
  <div className="ts-page-hero"><span className="ts-kicker">YOUR ACCOUNT · BILLING</span><h1>Your plan, payments<br/>and subscription.</h1><p>When configured, subscriptions are processed through Stripe-hosted Checkout and managed in Stripe's customer portal. This developer release accepts <strong>test payments only</strong>.</p></div>
  <div className="v7-billing-layout">
   <section className="ts-settings-card v7-billing-main"><div className="ts-section-icon"><CreditCard size={25}/></div>
    {!token?<><span className="ts-kicker">ACCOUNT REQUIRED</span><h2>Sign in to continue to payment.</h2><p>Your plan and invoices belong to your own verified account. We never ask you to enter card details directly into this website.</p><div className="v7-billing-buttons"><Link className="ts-btn-dark" href="/sign-in?next=%2Fbilling">Sign in to billing <ArrowRight size={17}/></Link><Link className="ts-btn-outline" href="/sign-up?next=%2Fbilling">Create an account</Link></div></>:
    <><span className="ts-kicker">SERVER-VERIFIED ACCOUNT STATUS</span><h2>{loading?'Loading plan…':isGrowth?'Growth plan':'Sandbox plan'}</h2><div className="ts-plan-status"><span>Restaurant</span><strong>{state?.name||'Your workspace'}</strong></div><div className="ts-plan-status"><span>Subscription</span><strong>{state?.subscription_status||'None'}</strong></div><div className="ts-plan-status"><span>Account AI analyst</span><strong>{state?.ai_enabled?'Available':'Not enabled'}</strong></div>
     <div className="v7-billing-buttons"><button type="button" className="ts-btn-dark" disabled={busy||loading||isGrowth||!canCheckout} onClick={()=>void action('checkout')}>Continue to Stripe test checkout <ExternalLink size={16}/></button><button type="button" className="ts-btn-outline" disabled={busy||loading||!state||!config?.test_checkout_configured||!config?.test_webhook_configured||state.subscription_status==='none'} onClick={()=>void action('portal')}>Manage test subscription <ExternalLink size={16}/></button><button type="button" className="ts-mini-button" onClick={()=>void refresh()} disabled={busy}><RefreshCcw size={15}/> Refresh plan status</button></div>
     {!canCheckout&&<div className="ts-alert">Stripe test checkout isn't configured on this server. The developer needs to add a test secret key and recurring Price ID. No payment has been attempted.</div>}
     </>}
    {message&&<div className="ts-alert" role="status">{message}</div>}
   </section>
   <aside className="v7-billing-aside"><div className="v7-billing-feature"><LockKeyhole size={21}/><strong>Account security</strong><p>Passwords are hashed locally and server-side sessions identify your workspace.</p></div><div className="v7-billing-feature"><ShieldCheck size={21}/><strong>Checkout security</strong><p>Stripe hosts the payment form. The server listens for signed subscription events.</p></div><div className="v7-billing-feature"><CheckCircle2 size={21}/><strong>Subscription management</strong><p>Update or cancel a test plan through the customer portal when configured.</p></div><div className="v7-billing-feature caution"><CreditCard size={21}/><strong>No live billing</strong><p>Actual charges and real restaurant onboarding remain disabled pending production readiness.</p></div></aside>
  </div>
  <div className="ts-caution"><ShieldCheck size={21}/><p>A successful checkout return does not activate a plan by itself. Subscription access follows a verified Stripe webhook and a refreshed server-side plan status. Never expose Stripe test secrets, database passwords, or authentication cookies in frontend code.</p></div>
 </main>
}
