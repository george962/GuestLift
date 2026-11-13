'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {ArrowRight,CheckCircle2,Eye,EyeOff,KeyRound,LockKeyhole} from 'lucide-react';
import {localAuthClient} from '@/lib/local-auth';

type Mode='sign-in'|'sign-up'|'forgot-password'|'reset-password';
const headings:Record<Mode,{tag:string,title:string,body:string}>={
 'sign-in':{tag:'WELCOME BACK',title:'Welcome back.',body:'Sign in to your restaurant workspace and manage your subscription.'},
 'sign-up':{tag:'GET STARTED',title:'Create your account.',body:'Save your restaurant profile, explore analytics and try subscription billing in test mode.'},
 'forgot-password':{tag:'LOCAL ACCOUNT RECOVERY',title:'Password recovery.',body:'Email recovery is not enabled in this local developer release.'},
 'reset-password':{tag:'ACCOUNT SECURITY',title:'Change your password.',body:'While signed in, confirm your current password before setting a new one.'}
};
const allowed=new Set(['/billing','/dashboard','/connections','/settings','/onboarding','/account']);
function safeNext(value:string|null){return value&&allowed.has(value)?value:'/dashboard'}

export function AuthPanel({mode}:{mode:Mode}){
 const router=useRouter();const sb=localAuthClient();
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[currentPassword,setCurrentPassword]=useState('');
 const [showPassword,setShowPassword]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [next,setNext]=useState('/dashboard'),[recoveryReady,setRecoveryReady]=useState(false);
 const words=headings[mode];
 useEffect(()=>{setNext(safeNext(new URLSearchParams(window.location.search).get('next')))},[]);
 useEffect(()=>{if(!sb||mode!=='reset-password')return;let mounted=true;
  void sb.auth.getSession().then(({data})=>{if(mounted)setRecoveryReady(Boolean(data.session))});
  const {data:listener}=sb.auth.onAuthStateChange((_event,session)=>{if(mounted)setRecoveryReady(Boolean(session))});
  return()=>{mounted=false;listener.subscription.unsubscribe()};
 },[sb,mode]);
 const loginHref='/sign-in?next='+encodeURIComponent(next);
 const signupHref='/sign-up?next='+encodeURIComponent(next);
 async function submit(e:React.FormEvent){e.preventDefault();setError('');setNotice('');
  if((mode==='sign-up'||mode==='reset-password')&&password!==confirm){setError('Passwords do not match.');return}
  setBusy(true);
  try{
   if(mode==='forgot-password'){setError('Email recovery is not configured for local development. Sign in to change your password.');return;}
   if(mode==='reset-password'){
    const {error}=await sb.auth.updateUser({password,current_password:currentPassword});if(error)throw error;
    setNotice('Password updated. Other signed-in devices have been logged out.');setCurrentPassword('');setPassword('');setConfirm('');return;
   }
   if(mode==='sign-up'){
    const {data,error}=await sb.auth.signUp({email,password});if(error)throw error;
    if(data.session){router.push(next==='/billing'?'/onboarding?next=billing':'/onboarding')}else{setNotice('Account created. Sign in to continue.')}return;
   }
   const {data,error}=await sb.auth.signInWithPassword({email,password});if(error)throw error;
   if(!data.session)throw new Error('No verified session was established.');router.push(next);
  }catch(e){setError(e instanceof Error?e.message:'The account request failed. Please try again.')}finally{setBusy(false)}
 }
 return <main className="ts-auth-page v7-auth-page"><div className="ts-auth-shell">
  <aside className="ts-auth-side v7-auth-side"><span className="ts-kicker">BUILT FOR RESTAURANT OPERATORS</span><h2>Every question about your restaurant.<br/><em>One clear workspace.</em></h2><p>See sales, guest behavior, promotion spending and evidence-backed answers—then return to the same workspace whenever you need it.</p>
   <div className="v7-auth-benefits"><span><CheckCircle2 size={17}/> Restaurant profile saved to your account</span><span><CheckCircle2 size={17}/> Server-verified subscription access</span><span><CheckCircle2 size={17}/> A free fictional demo before you commit</span></div>
   <Link href="/start">Explore the demo instead <ArrowRight size={16}/></Link></aside>
  <section className="ts-auth-card v7-auth-card"><div className="ts-auth-lock"><LockKeyhole size={21}/></div><span className="ts-kicker">{words.tag}</span><h1>{words.title}</h1><p>{words.body}</p>
   {mode==='sign-up'&&<div className="v7-signup-track"><span className="on">1 · Account</span><span>2 · Restaurant</span><span>3 · Plan</span></div>}
   {mode==='forgot-password'?<div className="ts-alert" role="status">Local accounts have no outgoing email service. If you can still sign in, use <Link href="/reset-password">Change Password</Link>. If you are locked out, recovery requires a developer-operated reset; do not delete the database.</div>:
   mode==='reset-password'&&!recoveryReady?<div className="ts-alert" role="alert">Sign in to change your password. <Link href="/sign-in">Go to sign in</Link>.</div>:
   <form className="ts-form" onSubmit={submit}>
    {mode!=='reset-password'&&<label>Email address<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@restaurant.com" required/></label>}
    {mode==='reset-password'&&<label>Current password<input type="password" autoComplete="current-password" value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)} required /></label>}
    {<label>{mode==='reset-password'?'New password':'Password'}<div className="v7-password-wrap"><input type={showPassword?'text':'password'} autoComplete={mode==='sign-in'?'current-password':'new-password'} minLength={mode==='sign-in'?1:12} value={password} onChange={e=>setPassword(e.target.value)} required placeholder={mode==='sign-in'?'Enter password':'At least 12 characters'}/><button type="button" aria-label={showPassword?'Hide password':'Show password'} onClick={()=>setShowPassword(x=>!x)}>{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></label>}
    {(mode==='sign-up'||mode==='reset-password')&&<label>Confirm password<input type={showPassword?'text':'password'} autoComplete="new-password" minLength={12} value={confirm} onChange={e=>setConfirm(e.target.value)} required placeholder="Re-enter your password"/></label>}
    <button type="submit" className="ts-btn-dark" disabled={busy}>{busy?'Please wait…':({'sign-in':'Sign in','sign-up':'Create account','forgot-password':'Send recovery email','reset-password':'Update password'} as const)[mode]} <ArrowRight size={17}/></button>
   </form>}
   {error&&<div className="ts-alert error" role="alert">{error}</div>}{notice&&<div className="ts-alert good" role="status"><CheckCircle2 size={17}/>{notice}</div>}
   <div className="ts-auth-links">{mode==='sign-in'?<><Link href="/forgot-password">Forgot password?</Link><span>New to TableSignal? <Link href={signupHref}>Create account</Link></span></>:<><Link href={loginHref}>Back to sign in</Link><Link href="/pricing">View pricing</Link></>}</div>
   <div className="ts-auth-disclaimer"><KeyRound size={15}/> Local PostgreSQL developer accounts only. No email recovery, real payments, or merchant uploads.</div>
  </section></div></main>
}
