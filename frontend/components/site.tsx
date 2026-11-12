'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {ArrowUpRight,ChartNoAxesCombined,Menu,X} from 'lucide-react';
import {useState} from 'react';
export function Brand(){return <Link href="/" className="brand" aria-label="GuestLift home"><span className="brand-mark"><ChartNoAxesCombined size={20} strokeWidth={2.4}/></span><span>guestlift<span className="brand-dot">.</span></span></Link>}
export function Nav(){
  const pathname=usePathname(); const [open,setOpen]=useState(false);
  const links=[{href:'/',label:'Overview'},{href:'/how-it-works',label:'How it works'},{href:'/demo',label:'Data pipeline'},{href:'/offers',label:'Offer studio'}];
  return <header className="nav-shell"><div className="nav-inner"><Brand/><nav className={'nav-links '+(open?'nav-open':'')} aria-label="Main navigation">
    {links.map(x=><Link onClick={()=>setOpen(false)} href={x.href} key={x.href} className={pathname===x.href?'active':''}>{x.label}</Link>)}
  </nav><Link className="nav-cta" href="/offers">Try the demo <ArrowUpRight size={16}/></Link><button className="nav-mobile-toggle" aria-label={open?'Close menu':'Open menu'} onClick={()=>setOpen(!open)}>{open?<X/>:<Menu/>}</button></div></header>
}
export function Footer(){return <footer className="footer"><div className="site-width footer-top"><div><Brand/><p>Better restaurant data.<br/>More confident decisions.</p></div><div className="footer-right"><Link href="/">Overview</Link><Link href="/how-it-works">How it works</Link><Link href="/demo">Pipeline demo</Link><Link href="/offers">Offer studio</Link><a href="https://github.com/george962/GuestLift" target="_blank" rel="noreferrer">GitHub <ArrowUpRight size={13}/></a></div></div><div className="site-width footer-bottom"><span>© 2026 GuestLift · Independent product prototype</span><span>All public demo records are fictional. Not affiliated with Toast or Square.</span></div></footer>}
