'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {ArrowRight,Menu,X,ArrowUpRight} from 'lucide-react';
import {useEffect,useState} from 'react';
import {supabaseClient} from '@/lib/supabase-client';
import {BrandMark} from './brand-mark';
export function Brand(){return <Link href="/" className="brand ts-brand" aria-label="TableSignal home"><span className="brand-mark"><BrandMark width={30} height={30}/></span><span>table<span className="ts-brand-teal">signal</span><span className="brand-dot">.</span></span></Link>}
export function Nav(){
 const pathname=usePathname(); const [open,setOpen]=useState(false),[signedIn,setSignedIn]=useState(false);
 const sb=supabaseClient();
 useEffect(()=>{if(!sb)return;let mounted=true;void sb.auth.getSession().then(({data})=>{if(mounted)setSignedIn(Boolean(data.session))});const {data}=sb.auth.onAuthStateChange((_event,session)=>{if(mounted)setSignedIn(Boolean(session))});return()=>{mounted=false;data.subscription.unsubscribe()}},[sb]);
 const links=[{href:'/product',label:'How it works'},{href:'/pricing',label:'Pricing'},{href:'/help',label:'Help'}];
 return <header className="nav-shell ts-header"><div className="nav-inner"><Brand/>
 <nav className={'nav-links '+(open?'nav-open':'')} aria-label="Main navigation">{links.map(l=><Link key={l.href} href={l.href} onClick={()=>setOpen(false)} className={pathname===l.href?'active':''}>{l.label}</Link>)}<Link href={signedIn?"/account":"/sign-in"} className="ts-nav-mobile-signin" onClick={()=>setOpen(false)}>{signedIn?"My account":"Sign in"}</Link></nav>
 <div className="ts-nav-actions"><Link className="ts-nav-signin" href={signedIn?"/account":"/sign-in"}>{signedIn?"My account":"Sign in"}</Link><Link className="nav-cta" href="/start">Try the demo <ArrowRight size={16}/></Link></div>
 <button className="nav-mobile-toggle" aria-label={open?'Close menu':'Open menu'} aria-expanded={open} onClick={()=>setOpen(!open)}>{open?<X/>:<Menu/>}</button>
 </div></header>
}
export function Footer(){return <footer className="footer ts-footer"><div className="site-width footer-top"><div><Brand/><p>Restaurant sales, guests and promotions.<br/>Clear answers, grounded in evidence.</p></div><div className="ts-footer-cols"><div><strong>Explore</strong><Link href="/product">How it works</Link><Link href="/workspace">Interactive demo</Link><Link href="/pricing">Pricing</Link></div><div><strong>Your account</strong><Link href="/sign-in">Sign in</Link><Link href="/sign-up">Create account</Link><Link href="/settings">Settings</Link><Link href="/billing">Billing</Link></div><div><strong>Resources</strong><Link href="/help">Help & FAQs</Link><Link href="/connect">Data sources</Link><a href="https://github.com/george962/GuestLift" rel="noreferrer" target="_blank">Project source <ArrowUpRight size={14}/></a></div></div></div><div className="site-width footer-bottom"><span>© 2026 TableSignal (working name). Independent demonstration.</span><span>Fictional data only · No live payments · No real merchant uploads</span></div></footer>}
