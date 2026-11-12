'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {ArrowRight,CheckCircle2,KeyRound,LockKeyhole,Mail,ShieldCheck} from 'lucide-react';
import {supabaseClient} from '@/lib/supabase-client';
type Mode='sign-in'|'sign-up'|'forgot-password'|'reset-password';
const headings:{[key in Mode]:{tag:string,title:string,body:string}}={
 'sign-in':{tag:'WELCOME BACK',title:'Sign in to your workspace.',body:'Your restaurant profile and subscription details live behind verified account access.'},
 'sign-up':{tag:'GET STARTED',title:'Create an account.',body:'Start an individual account workspace with fictional data. Real merchant onboarding comes later.'},
 'forgot-password':{tag:'ACCOUNT RECOVERY',title:'Reset your password.',body:'Enter the email associated with your configured account. We’ll send a recovery link.'},
 'reset-password':{tag:'ACCOUNT RECOVERY',title:'Choose a new password.',body:'Open this page from your email recovery link, then choose a new password.'}
};
export function AuthPanel({mode}:{mode:Mode}){
 const router=useRouter();const sb=supabaseClient();const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[confirm,setConfirm]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const words=headings[mode];
 async function submit(e:React.FormEvent){e.preventDefault();setError('');setNotice('');if(!sb)return;setBusy(true);
  try{
   if(mode==='forgot-password'){
    const {error}=await sb.auth.resetPasswordForEmail(email,{redirectTo:window.location.origin+'/reset-password'});if(error)throw error;
    setNotice('If that account exists, check its email for a password reset link. Add this redirect URL in Supabase settings.');return;
   }
   if(mode==='reset-password'){
    if(password!==confirm)throw new Error('Passwords do not match.');
    const {error}=await sb.auth.updateUser({password});if(error)throw error;
    setNotice('Password changed. You can now sign in.');return;
   }
   if(mode==='sign-up'){
    if(password!==confirm)throw new Error('Passwords do not match.');
    const {data,error}=await sb.auth.signUp({email,password,options:{emailRedirectTo:window.location.origin+'/sign-in'}});if(error)throw error;
    if(data.session){router.push('/onboarding')}else{setNotice('Check your email to verify your account, then return to Sign in.')}return;
   }
   const {data,error}=await sb.auth.signInWithPassword({email,password});if(error)throw error;
   if(!data.session)throw new Error('Your session was not established.');router.push('/workspace');
  }catch(e){setError(e instanceof Error?e.message:'Authentication request failed')}finally{setBusy(false)}
 }
 return <main className="ts-auth-page"><div className="ts-auth-shell"><aside className="ts-auth-side"><span className="ts-kicker">RESTO INTELLIGENCE, WITHOUT THE GUESSWORK</span><h2>Understand who returns. See what offers cost. Ask what to investigate.</h2><p>TableSignal brings restaurant sales, guest patterns and promotions into one clear workspace.</p><div><ShieldCheck size={20}/><span>Verified identity for account features. Fictional data only at this stage.</span></div><Link href="/workspace">Or explore without an account <ArrowRight size={16}/></Link></aside><section className="ts-auth-card"><div className="ts-auth-lock"><LockKeyhole size={22}/></div><span className="ts-kicker">{words.tag}</span><h1>{words.title}</h1><p>{words.body}</p>
  {!sb?<div className="ts-alert">Account sign-in is not configured on this deployment. Add the Supabase URL and publishable key to enable it. The fictional demo works without an account.</div>:
   <form className="ts-form" onSubmit={submit}>
    {mode!=='reset-password'&&<label>Email address<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@restaurant.com" required/></label>}
    {mode!=='forgot-password'&&<label>{mode==='reset-password'?'New password':'Password'}<input type="password" autoComplete={mode==='sign-in'?'current-password':'new-password'} minLength={8} value={password} onChange={e=>setPassword(e.target.value)} required placeholder="At least 8 characters"/></label>}
    {(mode==='sign-up'||mode==='reset-password')&&<label>Confirm password<input type="password" autoComplete="new-password" minLength={8} value={confirm} onChange={e=>setConfirm(e.target.value)} required placeholder="Re-enter password"/></label>}
    <button type="submit" className="ts-btn-dark" disabled={busy}>{busy?'Working…':({'sign-in':'Sign in','sign-up':'Create account','forgot-password':'Send reset link','reset-password':'Update password'} as const)[mode]} <ArrowRight size={17}/></button>
   </form>}
  {error&&<div className="ts-alert error" role="alert">{error}</div>}{notice&&<div className="ts-alert good" role="status"><CheckCircle2 size={17}/>{notice}</div>}
  <div className="ts-auth-links">{mode==='sign-in'?<><Link href="/forgot-password">Forgot password?</Link><span>New here? <Link href="/sign-up">Create account</Link></span></>:<><Link href="/sign-in">Back to sign in</Link><Link href="/pricing">See pricing</Link></>}</div>
  <div className="ts-auth-disclaimer"><KeyRound size={15}/> This is a developer preview, not an approved merchant-data service.</div>
 </section></div></main>
}
