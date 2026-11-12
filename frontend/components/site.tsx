'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {ArrowUpRight,Menu,X} from 'lucide-react';
import {useState} from 'react';
import {BrandMark} from './brand-mark';

export function Brand(){
  return <Link href="/" className="brand" aria-label="GuestLift home">
    <span className="brand-mark"><BrandMark width={30} height={30}/></span>
    <span>guestlift<span className="brand-dot">.</span></span>
  </Link>;
}
export function Nav(){
  const pathname=usePathname();const [open,setOpen]=useState(false);
  const links=[{href:'/',label:'Overview'},{href:'/import',label:'Import Lab'},{href:'/offers',label:'Offer Studio'},{href:'/how-it-works',label:'How it works'},{href:'/demo',label:'Pipeline detail'}];
  return <header className="nav-shell"><div className="nav-inner"><Brand/><nav className={'nav-links '+(open?'nav-open':'')} aria-label="Main navigation">
    {links.map(x=><Link onClick={()=>setOpen(false)} href={x.href} key={x.href} className={pathname===x.href?'active':''}>{x.label}</Link>)}
  </nav><Link className="nav-cta" href="/import">Try your data flow <ArrowUpRight size={16}/></Link>
  <button className="nav-mobile-toggle" aria-label={open?'Close menu':'Open menu'} onClick={()=>setOpen(!open)}>{open?<X/>:<Menu/>}</button></div></header>;
}
export function Footer(){return <footer className="footer"><div className="site-width footer-top"><div><Brand/><p>Two POS formats.<br/>One accountable reporting layer.</p></div><div className="footer-right"><Link href="/">Overview</Link><Link href="/import">Import Lab</Link><Link href="/offers">Offer Studio</Link><Link href="/how-it-works">Architecture</Link><a href="https://github.com/george962/GuestLift" target="_blank" rel="noreferrer">View source on GitHub <ArrowUpRight size={13}/></a></div></div><div className="site-width footer-bottom"><span>© 2026 GuestLift · Independent prototype</span><span>All public demo records are fictional. Not affiliated with Toast or Square.</span></div></footer>}
