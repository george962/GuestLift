'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,LogOut,Settings2,CreditCard,UserCircle2,ShieldCheck,CheckCircle2} from 'lucide-react';
import {accountApi,supabaseClient} from '@/lib/supabase-client';
type Workspace={name:string;plan:string;subscription_status:string;ai_enabled:boolean};
export default function Account(){const sb=supabaseClient();const [email,setEmail]=useState(''),[workspace,setWorkspace]=useState<Workspace|null>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(true);
 useEffect(()=>{if(!sb){setBusy(false);return}let mounted=true;
  void sb.auth.getSession().then(async({data})=>{if(!mounted)return;const token=data.session?.access_token;if(!token){setBusy(false);return}setEmail(data.session?.user.email||'');try{const r=await accountApi('/api/saas/me',token);if(mounted)setWorkspace(r.workspace)}catch(e){if(mounted)setMessage(e instanceof Error?e.message:'Profile unavailable')}finally{if(mounted)setBusy(false)}});
  const {data:listener}=sb.auth.onAuthStateChange((_event,session)=>{if(!mounted)return;if(!session){setEmail('');setWorkspace(null)}});return()=>{mounted=false;listener.subscription.unsubscribe()};
 },[sb]);
 async function out(){if(!sb)return;await sb.auth.signOut();setEmail('');setWorkspace(null);setMessage('Signed out successfully.')}
 return <main className="ts-public-page v7-account-page"><div className="ts-page-hero"><span className="ts-kicker">YOUR ACCOUNT</span><h1>{email?'One home for your business account.':'Your restaurant account starts here.'}</h1><p>{email?`Signed in as ${email}. Manage your business profile and subscription without leaving the product.`:'Create an account to keep a restaurant profile and manage a subscription in the configured test environment.'}</p></div>
  {email?<section className="v7-account-summary"><div><span className="ts-kicker">YOUR WORKSPACE</span><h2>{workspace?.name||'Your restaurant'}</h2><p>{email}</p></div><div><small>Plan</small><strong>{workspace?.plan==='growth'?'Growth':'Sandbox'}</strong><small>Subscription</small><strong>{workspace?.subscription_status||'None'}</strong></div></section>:
  <section className="v7-account-summary"><div><span className="ts-kicker">GET STARTED</span><h2>{!sb?'Sign-up requires configuration.':'Explore now, save your setup later.'}</h2><p>Fictional demo access is always available. Real merchant data remains unsupported.</p></div><div><Link className="ts-btn-dark" href="/sign-up">Create account <ArrowRight size={16}/></Link></div></section>}
  <div className="ts-action-cards v7-account-actions">{email?<><Link href="/workspace"><UserCircle2/> Open workspace <ArrowRight/></Link><Link href="/settings"><Settings2/> Restaurant settings <ArrowRight/></Link><Link href="/billing"><CreditCard/> Subscription & billing <ArrowRight/></Link><button onClick={()=>void out()}><LogOut/> Sign out <ArrowRight/></button></>:<><Link href="/sign-in"><UserCircle2/> Sign in <ArrowRight/></Link><Link href="/sign-up"><CheckCircle2/> Create account <ArrowRight/></Link><Link href="/workspace"><ShieldCheck/> Explore free demo <ArrowRight/></Link></>}</div>
  {busy&&<p className="ts-muted" style={{maxWidth:900,margin:'30px auto'}}>Checking account session…</p>}{message&&<div className="ts-alert" style={{maxWidth:900,margin:'25px auto'}}>{message}</div>}
 </main>
}
