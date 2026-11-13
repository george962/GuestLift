'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,Pause,Play,Users,TicketPercent,TrendingUp,Sparkles,CheckCircle2} from 'lucide-react';
import sample from '@/lib/demo-fallback.json';
import campaigns from '@/lib/campaign-demo.json';
import {summarizeWorkspace} from '@/lib/workspace-analytics.mjs';
import {evaluateCampaigns} from '@/lib/campaign-model.mjs';
import {usd} from '@/lib/types';
import type {Order} from '@/lib/types';
const orders=[...(sample.toast.records as Order[]),...(sample.square.records as Order[])];
const report=evaluateCampaigns(orders,campaigns.campaigns_csv,campaigns.redemptions_csv,35);
const stats=summarizeWorkspace(orders,report.campaigns);
const screens=[{title:'Sales overview',sub:'Know how your restaurant is performing',icon:TrendingUp,eyebrow:'01 · UNDERSTAND'},
 {title:'Guest behavior',sub:'See who returns and where identities are missing',icon:Users,eyebrow:'02 · DISCOVER'},
 {title:'Promotion costs',sub:'Understand the cost of every recorded offer',icon:TicketPercent,eyebrow:'03 · DECIDE'}];
export function MotionTour(){
 const [active,setActive]=useState(0);const [playing,setPlaying]=useState(true);
 useEffect(()=>{if(typeof window==='undefined')return; if(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches){setPlaying(false)}},[]);
 useEffect(()=>{if(!playing)return;const id=window.setInterval(()=>setActive(p=>(p+1)%screens.length),4400);return()=>window.clearInterval(id)},[playing]);
 const current=screens[active]; const Icon=current.icon;
 return <div className="ts-tour" aria-label="Animated restaurant analytics walkthrough">
   <div className="ts-tour-top"><div className="ts-tour-dots"><i/><i/><i/></div><span>Bluebird Kitchen · Fictional restaurant group</span><span className="ts-tour-live"><i/> SAMPLE DATA</span></div>
   <div className="ts-tour-layout"><aside className="ts-tour-rail"><span className="ts-tour-rail-brand">ts<span>.</span></span>{screens.map((s,i)=>{const I=s.icon;return <button key={s.title} className={active===i?'active':''} onClick={()=>{setActive(i);setPlaying(false)}} title={s.title} aria-label={'Preview '+s.title}><I size={19}/></button>})}<Link href="/workspace" aria-label="Open full demo"><Sparkles size={18}/></Link></aside>
   <div className="ts-tour-body" key={active}><div className="ts-tour-subhead"><span>{current.eyebrow}</span><span className="ts-tour-checked"><CheckCircle2 size={13}/> Computed from sample orders</span></div><h3><Icon size={21}/>{current.title}</h3><p>{current.sub}</p>
    {active===0&&<><div className="ts-tour-stats"><div><small>Net sales</small><strong>{usd(stats.net_sales_minor)}</strong></div><div><small>Orders</small><strong>{stats.orders}</strong></div><div><small>Discounts recorded</small><strong>{usd(stats.discount_minor)}</strong></div></div><div className="ts-mini-graph" aria-label="Animated illustrative sales trend">{[29,51,44,67,40,62,82,70,55,90,76,96,62,80].map((h,i)=><div key={i} style={{height:h+'%',animationDelay:(i*.07)+'s'}}/>)}</div></>}
    {active===1&&<><div className="ts-tour-stats"><div><small>Identified guests</small><strong>{stats.identified_customers}</strong></div><div><small>Observed repeat guests</small><strong>{stats.repeat_customers}</strong></div><div><small>Identity coverage</small><strong>{stats.identification_coverage_percent}%</strong></div></div><div className="ts-tour-segment"><span>Orders with known IDs</span><div><i style={{width:stats.identification_coverage_percent+'%'}}/></div><b>{stats.identification_coverage_percent}%</b></div><div className="ts-tour-insight"><Users size={16}/> Anonymous orders are excluded from guest-level conclusions.</div></>}
    {active===2&&<><div className="ts-tour-stats"><div><small>Campaigns</small><strong>{report.campaigns.length}</strong></div><div><small>Redemptions matched</small><strong>{report.campaigns.reduce((a,c)=>a+c.redeemed_orders,0)}</strong></div><div><small>Measured lift</small><strong>Unknown</strong></div></div><div className="ts-tour-insight"><TicketPercent size={16}/> Recorded discounts are measurable. Incremental profit needs a controlled test.</div><div className="ts-tour-campaign"><span>Compare offer spending</span>{report.campaigns.map((c,i)=><div key={c.campaign_id}><b>{c.name}</b><i style={{width:(36+i*20)+'%'}}/></div>)}</div></>}
   </div></div>
   <div className="ts-tour-bottom"><div className="ts-tour-controls">{screens.map((s,i)=><button key={i} onClick={()=>{setActive(i);setPlaying(false)}} className={active===i?'on':''} aria-label={'Go to '+s.title} />)}<button className="ts-tour-pause" onClick={()=>setPlaying(v=>!v)} aria-label={playing?'Pause walkthrough':'Play walkthrough'}>{playing?<Pause size={14}/>:<Play size={14}/>}</button></div><Link href="/workspace">Explore these numbers <ArrowRight size={15}/></Link></div>
 </div>
}
