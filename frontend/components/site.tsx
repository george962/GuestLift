'use client';
import Link from 'next/link';
import {usePathname,useRouter} from 'next/navigation';
import {ArrowRight,Menu,X,ArrowUpRight,LogOut,Settings2,Database,UserCircle2} from 'lucide-react';
import {useEffect,useState} from 'react';
import {localAuthClient} from '@/lib/local-auth';
import {BrandMark} from './brand-mark';

const appPaths=['/analyst','/guests','/dashboard','/opportunities','/experiments','/connections','/settings','/account','/billing','/onboarding','/reset-password'];
function isApp(pathname:string){return appPaths.some(p=>pathname===p||pathname.startsWith(p+'/'))}
export function Brand(){return <Link href="/" className="brand ts-brand" aria-label="TableSignal home"><span className="brand-mark"><BrandMark width={30} height={30}/></span><span>table<span className="ts-brand-teal">signal</span><span className="brand-dot">.</span></span></Link>}

export function Nav(){
 const pathname=usePathname();const router=useRouter();
 const [open,setOpen]=useState(false);const [signedIn,setSignedIn]=useState<boolean|null>(null);
 const [sessionWarning,setSessionWarning]=useState(false);
 const client=localAuthClient();
 useEffect(()=>{
  let active=true;
  void client.auth.getSession().then(({data,error})=>{
   if(!active)return;
   if(error){setSessionWarning(true);return;} // Network issues are not logouts.
   setSignedIn(Boolean(data.session));setSessionWarning(false);
  });
  const {data:listener}=client.auth.onAuthStateChange((_event,session)=>{
   if(active){setSignedIn(Boolean(session));setSessionWarning(false)}
  });
  return()=>{active=false;listener.subscription.unsubscribe()};
 },[client,pathname]);
 async function signOut(){
  const result=await client.auth.signOut();
  if(result.error){setSessionWarning(true);return}
  setSignedIn(false);setOpen(false);router.push('/sign-in');
 }
 const app=isApp(pathname);
 const primary=[{href:'/dashboard',label:'Overview'},{href:'/guests',label:'Guests'},{href:'/opportunities',label:'Opportunities'},{href:'/analyst',label:'AI analyst'},{href:'/experiments',label:'Experiments'}];
 const secondary=[{href:'/connections',label:'Data connection',icon:Database},{href:'/settings',label:'Restaurant settings',icon:Settings2},{href:'/billing',label:'Subscription & billing',icon:ArrowUpRight},{href:'/account',label:'My account',icon:UserCircle2}];
 if(app)return <header className="ts10-header">
  <div className="ts10-header-inner"><div className="ts10-header-brand"><Brand/><span className="ts10-workspace-label">/ My restaurant</span></div>
   <nav className={'ts10-primary-nav '+(open?'open':'')} aria-label="Restaurant navigation">
    {primary.map(x=><Link key={x.label} href={x.href} onClick={()=>setOpen(false)} className={pathname===x.href?'active':''}>{x.label}</Link>)}
   </nav>
   <div className="ts10-account-menu"><Link href="/connections" className="ts10-nav-connect">Data <Database size={15}/></Link>
    <details><summary><UserCircle2 size={19}/> Account</summary><div className="ts10-menu-contents">{secondary.map(x=><Link key={x.href} href={x.href} onClick={()=>setOpen(false)}><x.icon size={16}/>{x.label}</Link>)}{signedIn&&<button onClick={()=>void signOut()}><LogOut size={16}/> Sign out</button>}{signedIn===false&&<Link href="/sign-in">Sign in</Link>}</div></details>
   </div>
   <button className="ts10-menu-toggle" aria-label={open?'Close navigation':'Open navigation'} aria-expanded={open} onClick={()=>setOpen(x=>!x)}>{open?<X/>:<Menu/>}</button>
  </div>
  {sessionWarning&&<div className="ts10-session-warning" role="status">Account connection unavailable. Your session may still be active. <button onClick={()=>window.location.reload()}>Retry</button></div>}
 </header>;
 const links=[{href:'/product',label:'How it works'},{href:'/pricing',label:'Pricing'},{href:'/help',label:'Help'}];
 return <header className="nav-shell ts-header"><div className="nav-inner"><Brand/>
  <nav className={'nav-links '+(open?'nav-open':'')} aria-label="Public navigation">{links.map(l=><Link key={l.href} href={l.href} onClick={()=>setOpen(false)} className={pathname===l.href?'active':''}>{l.label}</Link>)}<Link href={signedIn?'/dashboard':'/sign-in'} onClick={()=>setOpen(false)} className="ts-nav-mobile-signin">{signedIn?'My restaurant':'Sign in'}</Link></nav>
  <div className="ts-nav-actions"><Link className="ts-nav-signin" href={signedIn?'/dashboard':'/sign-in'}>{signedIn?'My restaurant':'Sign in'}</Link><Link className="nav-cta" href="/start">Try the demo <ArrowRight size={16}/></Link></div>
  <button className="nav-mobile-toggle" aria-label={open?'Close menu':'Open menu'} aria-expanded={open} onClick={()=>setOpen(!open)}>{open?<X/>:<Menu/>}</button>
 </div></header>;
}
export function Footer(){const pathname=usePathname();if(isApp(pathname))return null;
 return <footer className="footer ts-footer"><div className="site-width footer-top"><div><Brand/><p>Understand returning guests, evaluate promotion costs, and keep your decisions in one place.</p></div><div className="ts-footer-cols"><div><strong>Explore</strong><Link href="/product">How it works</Link><Link href="/workspace">Interactive demo</Link><Link href="/pricing">Pricing</Link></div><div><strong>Your restaurant</strong><Link href="/sign-in">Sign in</Link><Link href="/sign-up">Create account</Link><Link href="/dashboard">Overview</Link><Link href="/opportunities">Opportunities</Link><Link href="/analyst">AI analyst</Link><Link href="/experiments">Saved decisions</Link></div><div><strong>Support</strong><Link href="/help">Help</Link><Link href="/connections">Data sources</Link><a href="https://github.com/george962/GuestLift" rel="noreferrer" target="_blank">Source <ArrowUpRight size={14}/></a></div></div></div><div className="site-width footer-bottom"><span>© 2026 TableSignal (working name).</span><span>Local developer preview · Synthetic data and test payments only</span></div></footer>}
