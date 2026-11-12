'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, Menu, X, ChartNoAxesCombined, Instagram, Github } from 'lucide-react';
import { useState } from 'react';

export function Brand(){return <Link href="/" className="brand"><span className="brand-mark"><ChartNoAxesCombined size={21} strokeWidth={2.6}/></span><span>guestlift<span className="brand-dot">.</span></span></Link>}
export function Nav(){
  const pathname=usePathname(); const [open,setOpen]=useState(false);
  const links=[{href:'/',label:'Home'},{href:'/how-it-works',label:'How it works'},{href:'/demo',label:'Interactive demo'}];
  return <header className="nav-shell"><div className="nav-inner"><Brand/><nav className={'nav-links '+(open?'nav-open':'')}>
    {links.map(x=><Link onClick={()=>setOpen(false)} href={x.href} key={x.href} className={pathname===x.href?'active':''}>{x.label}</Link>)}
    <Link className="mobile-cta" href="/demo" onClick={()=>setOpen(false)}>Explore the demo <ArrowUpRight size={16}/></Link>
  </nav><Link className="nav-cta" href="/demo">Launch demo <ArrowUpRight size={16}/></Link><button className="nav-mobile-toggle" aria-label={open?'Close menu':'Open menu'} onClick={()=>setOpen(!open)}>{open?<X/>:<Menu/>}</button></div></header>
}
export function Footer(){return <footer className="footer"><div className="site-width footer-top"><div><Brand/><p>Turning fragmented restaurant data<br/>into decisions you can trust.</p></div><div className="footer-right"><Link href="/">Home</Link><Link href="/how-it-works">Architecture</Link><Link href="/demo">Demo</Link><a href="https://github.com/george962/GuestLift" target="_blank" rel="noreferrer">GitHub <ArrowUpRight size={13}/></a></div></div><div className="site-width footer-bottom"><span>© 2026 GuestLift · Independent prototype</span><span>No real merchant data, testimonials, or financial results.</span></div></footer>}
