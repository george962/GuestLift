'use client';
import {useMemo,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,CheckCircle2,Database,FileSpreadsheet,GitMerge,Receipt} from 'lucide-react';
import payload from '@/lib/demo-fallback.json';
import {calculateMetrics,usd} from '@/lib/types';
import type {Order,Provider} from '@/lib/types';

export function LiveTeaser(){
  const [provider,setProvider]=useState<Provider>('toast');
  const [orderIndex,setOrderIndex]=useState(0);
  const orders=payload[provider].records as Order[];
  const order=orders[orderIndex % orders.length];
  const metrics=useMemo(()=>calculateMetrics(orders),[orders]);
  return <section className="gl-live-teaser" aria-label="Interactive example order transformation">
    <div className="gl-live-top"><span><span className="gl-dot gl-dot-teal"/> GUESTLIFT / EXAMPLE TRANSACTION</span><small>SWITCH DATA SOURCE ↓</small></div>
    <div className="gl-live-choice"><button className={provider==='toast'?'selected':''} onClick={()=>{setProvider('toast');setOrderIndex(0)}}>Toast CSV</button><button className={provider==='square'?'selected':''} onClick={()=>{setProvider('square');setOrderIndex(0)}}>Square JSON</button></div>
    <div className="gl-live-flow"><div><FileSpreadsheet size={16}/><span>{provider==='toast'?'CSV input':'JSON input'}</span></div><ArrowRight size={14}/><div><GitMerge size={16}/><span>Adapter</span></div><ArrowRight size={14}/><div className="valid"><Database size={16}/><span>GRDC</span></div></div>
    <div className="gl-live-record"><div className="gl-live-heading"><div><span className="gl-live-overline">CANONICAL ORDER</span><strong>{order.source_order_id}</strong><small>{order.location_id}</small></div><span className="gl-live-verified"><CheckCircle2 size={16}/> Sample normalized</span></div><div className="gl-live-fields"><div><span>Item gross</span><strong>{usd(order.gross_minor)}</strong></div><div><span>Discount</span><strong>−{usd(order.discount_minor)}</strong></div><div><span>Refunds</span><strong>−{usd(order.refund_minor)}</strong></div><div className="highlight"><span>Net sales</span><strong>{usd(order.net_sales_minor)}</strong></div></div></div>
    <div className="gl-live-foot"><div><span>FROM THIS SOURCE</span><strong>{orders.length} <small>sample orders</small> · {usd(metrics.net_sales_minor)}</strong></div><button onClick={()=>setOrderIndex(v=>(v+1)%orders.length)}><Receipt size={15}/> Next sample order</button></div>
    <Link className="gl-live-cta" href="/import">Upload and validate synthetic files yourself <ArrowRight size={17}/></Link>
  </section>;
}
