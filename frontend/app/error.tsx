'use client';
import {useEffect} from 'react';
import Link from 'next/link';
import {accountApi,localAuthClient} from '@/lib/local-auth';
export default function ErrorPage({reset}:{error:Error&{digest?:string};reset:()=>void}){
 useEffect(()=>{
  // Record an allowlisted event only. Never transmit stack traces, URL query strings, or PII.
  void localAuthClient().auth.getSession().then(({data})=>{
   const token=data.session?.access_token;
   if(token)void accountApi('/api/readiness/event',token,'POST',{event:'client_error'}).catch(()=>{});
  }).catch(()=>{});
 },[]);
 return <main id="main-content" className="ts10-app" role="alert"><section className="ts10-card ts10-empty">
  <h1>This page could not load.</h1><p>Your saved restaurant data was not changed. Try the page again or check your Square connection.</p>
  <div className="ts10-actions"><button className="ts10-primary" onClick={()=>reset()}>Try again</button><Link href="/connections" className="ts10-secondary">Check data connection</Link><Link href="/support" className="ts10-secondary">Report a problem</Link></div>
 </section></main>;
}
