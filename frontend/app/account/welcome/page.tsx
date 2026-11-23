'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {ArrowRight,CheckCircle2,ShieldCheck} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

type Status='checking'|'ready'|'signed-out'|'offline';
export default function Welcome(){
 const router=useRouter();
 const [status,setStatus]=useState<Status>('checking');
 const [token,setToken]=useState('');
 const [accepted,setAccepted]=useState(false);
 const [stored,setStored]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 useEffect(()=>{
  let live=true;
  void localAuthClient().auth.getSession().then(async({data,error:e})=>{
    if(!live)return;
    if(e){setStatus('offline');setError(e.message);return;}
    const t=data.session?.access_token||'';
    if(!t){setStatus('signed-out');return;}
    setToken(t);
    try{
     const r=await accountApi('/api/readiness/preview',t) as {acknowledged:boolean};
     if(live){setStored(r.acknowledged);setStatus('ready');}
    }catch(err){if(live){setStatus('offline');setError(err instanceof Error?err.message:'Preview notice unavailable.');}}
  });
  return()=>{live=false;};
 },[]);
 async function continueSetup(){
  if(!stored&&!accepted)return;
  if(stored){router.push('/onboarding');return;}
  setBusy(true);setError('');
  try{
    await accountApi('/api/readiness/preview',token,'POST',{
      version:'sandbox-preview-2026-11',acknowledged:true
    });
    setStored(true);router.push('/onboarding');
  }catch(e){setError(e instanceof Error?e.message:'Could not record your acknowledgement.');}
  finally{setBusy(false);}
 }
 return <main id="main-content" className="ts10-app"><div className="ts10-card ts10-empty">
  <CheckCircle2 size={42} color="#16866a"/><span className="ts10-eyebrow">ACCOUNT CREATED · DEVELOPER PREVIEW</span>
  <h1>{status==='ready'?'Your TableSignal account is ready.':status==='checking'?'Checking your new account…':status==='offline'?'Account connection unavailable':'Welcome to TableSignal'}</h1>
  {status==='ready'&&<>
   <p>Before connecting a test seller, confirm that you understand this developer preview.</p>
   <section className="ts-m6-ack" aria-label="Developer preview notice">
    <p><strong>Sandbox only:</strong> Use simulated Square test data, not real customer information. No live payments or merchant connection are enabled. Our <Link href="/terms">Terms</Link> and <Link href="/privacy">Privacy Policy</Link> are drafts pending legal review.</p>
    {!stored&&<label className="ts-m6-checkbox"><input type="checkbox" checked={accepted} onChange={e=>setAccepted(e.target.checked)}/> I understand these developer-preview limits.</label>}
    {stored&&<p role="status">Preview acknowledgement recorded.</p>}
   </section>
   <div className="ts10-actions"><button type="button" className="ts10-primary" disabled={busy||(!accepted&&!stored)} onClick={()=>void continueSetup()}>
     {busy?'Saving…':'Set up my restaurant'} <ArrowRight size={16}/>
   </button></div>
  </>}
  {status==='signed-out'&&<><p>Sign in to set up your restaurant.</p><Link href="/sign-in" className="ts10-primary">Sign in</Link></>}
  {status==='offline'&&<><p>We could not verify your session or save consent. No acknowledgement was recorded.</p><button type="button" onClick={()=>window.location.reload()}>Retry</button></>}
  {error&&<div role="alert" className="ts10-notice ts10-danger">{error}</div>}
  <div className="ts10-notice"><ShieldCheck size={16}/> This acknowledgement is not acceptance of final legal terms. A separate review is required before launch.</div>
 </div></main>;
}
