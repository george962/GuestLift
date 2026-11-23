'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,LifeBuoy,ShieldCheck} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

type Category='connection'|'data_quality'|'billing'|'account'|'other';
export default function Support(){
 const [token,setToken]=useState('');
 const [checking,setChecking]=useState(true);
 const [category,setCategory]=useState<Category>('connection');
 const [description,setDescription]=useState('');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [success,setSuccess]=useState('');
 useEffect(()=>{let active=true;void localAuthClient().auth.getSession().then(({data,error})=>{
   if(active){setChecking(false);setToken(data.session?.access_token||'');if(error)setError(error.message);}
 });return()=>{active=false;}},[]);
 async function submit(e:React.FormEvent){
  e.preventDefault();if(!token)return;
  setBusy(true);setError('');setSuccess('');
  try{
   const result=await accountApi('/api/readiness/support',token,'POST',{category,description});
   setSuccess(`Request ${result.request_id} was saved for developer review. No notification was sent and no reply is guaranteed.`);
   setDescription('');
  }catch(err){setError(err instanceof Error?err.message:'The request could not be recorded.');}
  finally{setBusy(false);}
 }
 return <main id="main-content" className="ts10-app">
  <div className="ts10-heading"><span className="ts9-kicker">CUSTOMER READINESS · HELP</span><h1>Contact developer support.</h1><p>Describe an issue with this test workspace. Requests are stored; this is not yet a staffed customer-support service.</p></div>
  {checking&&<div className="ts10-notice" role="status">Checking your session…</div>}
  {!checking&&!token&&<section className="ts10-card"><h2>Sign in to submit a request</h2><Link className="ts10-primary" href="/sign-in?next=%2Fsupport">Sign in <ArrowRight size={16}/></Link></section>}
  {token&&<section className="ts10-card"><LifeBuoy size={30}/><h2>Describe the problem</h2>
   <p className="ts10-small">Include a reproducible action and the page you were using. Do not include passwords, access tokens, payment details or guest information.</p>
   <form className="ts-form" onSubmit={e=>void submit(e)}>
    <label>Issue category<select value={category} onChange={e=>setCategory(e.target.value as Category)}>
     <option value="connection">Square connection</option><option value="data_quality">Numbers or data quality</option><option value="billing">Test billing</option><option value="account">Account access</option><option value="other">Other</option></select></label>
    <label>Issue description<textarea rows={5} required minLength={12} maxLength={500} value={description} onChange={e=>setDescription(e.target.value)} placeholder="What happened, what did you expect, and where?"/></label>
    <button className="ts10-primary" type="submit" disabled={busy||description.trim().length<12}>{busy?'Saving…':'Log support request'} <ArrowRight size={16}/></button>
   </form>
  </section>}
  {error&&<div className="ts10-notice ts10-danger" role="alert">{error}</div>}
  {success&&<div className="ts10-notice" role="status">{success}</div>}
  <div className="ts10-notice"><ShieldCheck size={18}/> Only development/Sandbox problems should be submitted. No live customer information is permitted. <Link href="/help">Help center</Link></div>
 </main>;
}
