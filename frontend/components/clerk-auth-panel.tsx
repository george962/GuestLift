'use client';
import {useEffect,useState} from 'react';
import {SignIn,SignUp,UserProfile} from '@clerk/nextjs';
import {safeNext} from '@/lib/safe-next';

type Mode='sign-in'|'sign-up'|'forgot-password'|'reset-password';

/** Managed sign-in (Clerk): email verification, password reset and MFA are handled by Clerk's screens. */
export function ClerkAuthPanel({mode}:{mode:Mode}){
 const [next,setNext]=useState('/dashboard');
 useEffect(()=>{setNext(safeNext(new URLSearchParams(window.location.search).get('next')))},[]);
 const withNext=(path:string)=>path+'?next='+encodeURIComponent(next);
 return <main className="ts-auth-page v7-auth-page"><div className="ts-auth-shell" style={{justifyContent:'center'}}>
  <section style={{display:'grid',placeItems:'center',padding:'32px 0',width:'100%'}}>
   {mode==='sign-up'
     ?<SignUp routing="hash" signInUrl={withNext('/sign-in')} forceRedirectUrl={next==='/dashboard'?'/account/welcome':next}/>
     :mode==='reset-password'
       ?<UserProfile routing="hash"/>
       :<SignIn routing="hash" signUpUrl={withNext('/sign-up')} forceRedirectUrl={next}/>}
  </section>
 </div></main>;
}
