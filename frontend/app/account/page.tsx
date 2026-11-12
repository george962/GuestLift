'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,LogOut,Settings2,CreditCard,UserCircle2} from 'lucide-react';
import {supabaseClient} from '@/lib/supabase-client';
export default function Account(){const sb=supabaseClient();const [email,setEmail]=useState('');
 useEffect(()=>{if(!sb)return;void sb.auth.getUser().then(({data})=>setEmail(data.user?.email||''))},[sb]);
 async function out(){if(!sb)return;await sb.auth.signOut();setEmail('')}
 return <main className="ts-public-page"><div className="ts-page-hero"><span className="ts-kicker">ACCOUNT</span><h1>{email?'Your account, in one place.':'Sign in to manage your account.'}</h1><p>{email?`Signed in as ${email}. Your billing and restaurant profile have dedicated pages.`:'Create an account or sign in to manage your restaurant profile and test subscription.'}</p></div><div className="ts-action-cards">{email?<><Link href="/settings"><Settings2/>Restaurant profile <ArrowRight/></Link><Link href="/billing"><CreditCard/>Billing and plan <ArrowRight/></Link><button onClick={out}><LogOut/>Sign out <ArrowRight/></button></>:<><Link href="/sign-in"><UserCircle2/>Sign in <ArrowRight/></Link><Link href="/sign-up"><UserCircle2/>Create account <ArrowRight/></Link></>}</div></main>}
