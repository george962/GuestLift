'use client';
import {useMemo,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,ArrowUpRight,BarChart3,CheckCircle2,MapPin,Sparkles,TicketPercent,Users,Wallet} from 'lucide-react';
import ordersJson from '@/lib/demo-fallback.json';
import campaignJson from '@/lib/campaign-demo.json';
import {summarizeWorkspace,askWorkspace} from '@/lib/workspace-analytics.mjs';
import {evaluateCampaigns} from '@/lib/campaign-model.mjs';
import {usd} from '@/lib/types';
import type {Order} from '@/lib/types';
const orders=[...(ordersJson.toast.records as Order[]),...(ordersJson.square.records as Order[])];
const campaign=evaluateCampaigns(orders,campaignJson.campaigns_csv,campaignJson.redemptions_csv,35);
const stats=summarizeWorkspace(orders,campaign.campaigns);
const choices=[{title:'Sales',icon:Wallet,q:'Summarize my sales'},{title:'Customers',icon:Users,q:'What do we know about returning customers?'},{title:'Promotions',icon:TicketPercent,q:'How much did the coupons cost?'}];
export function OutcomePreview(){const [sel,setSel]=useState(0);const found=useMemo(()=>askWorkspace(choices[sel].q,stats),[sel]);const max=Math.max(...stats.locations.map(l=>l.net_sales_minor),1);
return <div className="gx-preview" aria-label="Interactive synthetic restaurant intelligence demonstration"><div className="gx-preview-top"><div><span className="gx-status-dot"/> Bluebird Kitchen Group <small>Demo workspace</small></div><span>FICTIONAL DATA</span></div><div className="gx-preview-body"><div className="gx-preview-tabs">{choices.map((c,i)=>{const Icon=c.icon;return <button className={i===sel?'selected':''} onClick={()=>setSel(i)} key={c.title}><Icon size={15}/>{c.title}</button>})}</div><div className="gx-preview-kpi"><div><span>{sel===0?'Observed net sales':sel===1?'Identified repeat customers':'Recorded campaign discounts'}</span><strong>{sel===0?usd(stats.net_sales_minor):sel===1?String(stats.repeat_customers):usd(stats.campaigns.reduce((s,c)=>s+c.discount_minor,0))}</strong><small>{sel===0?`${stats.orders} observed sample orders`:sel===1?`${stats.identification_coverage_percent}% ID coverage`:`${stats.campaigns.length} fictional campaigns`}</small></div><BarChart3 size={30}/></div><div className="gx-preview-chart"><div className="gx-preview-chart-title"><span><MapPin size={14}/> Location comparison</span><small>Fictional sample</small></div>{stats.locations.slice(0,3).map(l=><div className="gx-preview-row" key={l.location}><small>{l.location.split(':')[1]}</small><div><i style={{width:`${l.net_sales_minor/max*100}%`}}/></div><b>{usd(l.net_sales_minor)}</b></div>)}</div><div className="gx-preview-answer"><span><Sparkles size={14}/> GUESTLIFT ANALYST · EVIDENCE-BASED</span><p>{found.answer}</p><div><CheckCircle2 size={14}/> Sources: {found.evidence_keys.slice(0,2).join(' · ')}</div></div></div><div className="gx-preview-foot"><span>One dataset. Sales, customers and campaigns.</span><Link href="/workspace">Explore <ArrowUpRight size={14}/></Link></div></div>
}
