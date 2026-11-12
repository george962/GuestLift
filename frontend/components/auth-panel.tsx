'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {ArrowRight,CheckCircle2,Eye,EyeOff,KeyRound,LockKeyhole,ShieldCheck,Sparkles} from 'lucide-react';
import {supabaseClient} from '@/lib/supabase-client';

type Mode='sign-in'|'sign-up'|'forgot-password'|'reset-password';
const headings:Record<Mode,{tag:string,title:string,body:string}>={
 'sign-in':{tag:'WELCOME BACK',title:'Welcome back.',body:'Sign in to your restaurant workspace and manage your subscription.'},
 'sign-up':{tag:'GET STARTED',title:'Create your account.',body:'Save your restaurant profile, explore analytics and try subscription billing in test mode.'},
 'forgot-password':{tag:'ACCOUNT RECOVERY',title:'Reset your password.',body:'We will send a secure recovery link to your email address.'},
 'reset-password':{tag:'ACCOUNT RECOVERY',title:'Choose a new password.',body:'Use the password recovery link sent to your email, then create a new password.'}
};
const allowed=new Set(['/billing','/workspace','/settings','/onboarding','/account']);
function safeNext(value:string|null){return value&&allowed.has(value)?value:'/workspace'}

export function AuthPanel({mode}:{mode:Mode}){
 const router=useRouter();const sb=supabaseClient();
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[confirm,setConfirm]=useState('');
 const [showPassword,setShowPassword]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [next,setNext]=useState('/workspace'),[recoveryReady,setRecoveryReady]=useState(false);
 const words=headings[mode];
 useEffect(()=>{setNext(safeNext(new URLSearchParams(window.location.search).get('next')))},[]);
 useEffect(()=>{if(!sb||mode!=='reset-password')return;let mounted=true;
  void sb.auth.getSession().then(({data})=>{if(mounted)setRecoveryReady(Boolean(data.session))});
  const {data:listener}=sb.auth.onAuthStateChange((_event,session)=>{if(mounted)setRecoveryReady(Boolean(session))});
  return()=>{mounted=false;listener.subscription.unsubscribe()};
 },[sb,mode]);
 const loginHref='/sign-in?next='+encodeURIComponent(next);
 const signupHref='/sign-up?next='+encodeURIComponent(next);
 async function submit(e:React.FormEvent){e.preventDefault();setError('');setNotice('');if(!sb){setError('Account provider is not configured.');return}
  if((mode==='sign-up'||mode==='reset-password')&&password!==confirm){setError('Passwords do not match.');return}
  setBusy(true);
  try{
   if(mode==='forgot-password'){
    const {error}=await sb.auth.resetPasswordForEmail(email,{redirectTo:window.location.origin+'/reset-password'});if(error)throw error;
    setNotice('If this address has an account, a recovery email has been sent. Check your inbox and spam folder.');return;
   }
   if(mode==='reset-password'){
    const {error}=await sb.auth.updateUser({password});if(error)throw error;
    setNotice('Password updated. You can sign in with the new password.');return;
   }
   if(mode==='sign-up'){
    const {data,error}=await sb.auth.signUp({email,password,options:{emailRedirectTo:window.location.origin+loginHref}});if(error)throw error;
    if(data.session){router.push(next==='/billing'?'/onboarding?next=billing':'/onboarding')}else{setNotice('Check your email for a confirmation link. Once confirmed, sign in to continue.')}return;
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
   {!sb?<div className="ts-alert" role="status"><b>Account setup is not active yet.</b> The site owner needs to add Supabase credentials to the deployment. The public fictional demo still works.<div style={{marginTop:12}}><Link href="/workspace">Open free demo <ArrowRight size={14}/></Link></div></div>:
   mode==='reset-password'&&!recoveryReady?<div className="ts-alert" role="alert">Open this page using the recovery link in your email. If the link expired, <Link href="/forgot-password">request another one</Link>.</div>:
   <form className="ts-form" onSubmit={submit}>
    {mode!=='reset-password'&&<label>Email address<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@restaurant.com" required/></label>}
    {mode!=='forgot-password'&&<label>{mode==='reset-password'?'New password':'Password'}<div className="v7-password-wrap"><input type={showPassword?'text':'password'} autoComplete={mode==='sign-in'?'current-password':'new-password'} minLength={mode==='sign-in'?8:10} value={password} onChange={e=>setPassword(e.target.value)} required placeholder={mode==='sign-in'?'Enter password':'At least 10 characters'}/><button type="button" aria-label={showPassword?'Hide password':'Show password'} onClick={()=>setShowPassword(x=>!x)}>{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></label>}
    {(mode==='sign-up'||mode==='reset-password')&&<label>Confirm password<input type={showPassword?'text':'password'} autoComplete="new-password" minLength={10} value={confirm} onChange={e=>setConfirm(e.target.value)} required placeholder="Re-enter your password"/></label>}
    <button type="submit" className="ts-btn-dark" disabled={busy}>{busy?'Please wait…':({'sign-in':'Sign in','sign-up':'Create account','forgot-password':'Send recovery email','reset-password':'Update password'} as const)[mode]} <ArrowRight size={17}/></button>
   </form>}
   {error&&<div className="ts-alert error" role="alert">{error}</div>}{notice&&<div className="ts-alert good" role="status"><CheckCircle2 size={17}/>{notice}</div>}
   <div className="ts-auth-links">{mode==='sign-in'?<><Link href="/forgot-password">Forgot password?</Link><span>New to TableSignal? <Link href={signupHref}>Create account</Link></span></>:<><Link href={loginHref}>Back to sign in</Link><Link href="/pricing">View pricing</Link></>}</div>
   <div className="ts-auth-disclaimer"><KeyRound size={15}/> Accounts require configured Supabase Auth. Test billing only. No real merchant uploads yet.</div>
  </section></div></main>
}
