'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {SESSION_EXPIRED_EVENT} from '@/lib/auth-mode';

/** Shown when the API rejects the session, so an expired login never looks like missing data. */
export function SessionExpiredBanner(){
 const [expired,setExpired]=useState(false);
 useEffect(()=>{const on=()=>setExpired(true);window.addEventListener(SESSION_EXPIRED_EVENT,on);return()=>window.removeEventListener(SESSION_EXPIRED_EVENT,on)},[]);
 if(!expired)return null;
 const next=typeof window!=='undefined'?encodeURIComponent(window.location.pathname):'';
 return <div role="alert" className="ts-alert error" style={{position:'sticky',top:'env(safe-area-inset-top, 0px)',zIndex:50,margin:0,borderRadius:0,textAlign:'center'}}>
  Your session has ended. <Link href={`/sign-in?next=${next}`}>Sign in again</Link> to continue.
 </div>;
}
