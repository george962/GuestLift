'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,CheckCircle2,ShieldCheck,Store} from 'lucide-react';
import {localAuthClient} from '@/lib/local-auth';
export default function Welcome(){
 const [status,setStatus]=useState<'checking'|'ready'|'signed-out'|'offline'>('checking');
 useEffect(()=>{void localAuthClient().auth.getSession().then(({data,error})=>setStatus(error?'offline':data.session?'ready':'signed-out'))},[]);
 return <main className="ts10-app"><div className="ts10-card ts10-empty"><CheckCircle2 size={42} color="#16866a"/><span className="ts10-eyebrow">ACCOUNT CREATED · LOCAL DEVELOPMENT</span>
  <h1>{status==='ready'?'Your TableSignal account is ready.':status==='checking'?'Checking your new account…':status==='offline'?'Account connection unavailable':'Welcome to TableSignal'}</h1>
  <p>{status==='ready'?'Your sign-in is saved in a secure browser cookie. Next, tell us about your restaurant and connect your Square Sandbox test data.':status==='offline'?'Try refreshing this page. A temporary connection failure does not mean you were signed out.':'Your restaurant workspace is protected by your account.'}</p>
  <div className="ts10-actions">{status==='ready'?<Link href="/onboarding" className="ts10-primary"><Store size={17}/> Set up my restaurant <ArrowRight size={16}/></Link>:<Link href="/sign-in" className="ts10-primary">Sign in <ArrowRight size={16}/></Link>}{status==='offline'&&<button className="ts10-secondary" onClick={()=>window.location.reload()}>Retry</button>}</div>
  <div className="ts10-notice"><ShieldCheck size={16}/> This is a local developer account. Email recovery and live merchant connections are not available yet.</div>
 </div></main>
}
