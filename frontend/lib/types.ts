export type Provider = 'toast' | 'square';
export type Item = {item_id:string;name:string;quantity:number;gross_minor:number;discount_minor:number};
export type Payment = {payment_id:string;amount_minor:number;status:string};
export type Order = {provider:Provider;source_order_id:string;location_id:string;created_at:string;currency:string;status:string;customer_id?:string|null;gross_minor:number;discount_minor:number;refund_minor:number;net_sales_minor:number;tax_minor:number|null;tip_minor:number|null;items:Item[];payments:Payment[];lineage:Record<string,string>;warnings:string[]};
export type Preview = {provider:Provider;records:Order[];summary:{orders:number;items:number;payments:number;net_sales_minor:number;discounts_minor:number;refunds_minor:number};files?:Record<string,string>;raw_file?:string;raw_snippet?:string};
export type Metrics = {order_count:number;net_sales_minor:number;discounts_minor:number;refunds_minor:number;average_order_minor:number;orders:Order[];locations:{location_id:string;provider:string;orders:number;net_sales_minor:number;discounts_minor:number;refunds_minor:number}[]};
export const usd = (cents:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(cents/100);
export const fmtInt = (n:number)=>new Intl.NumberFormat('en-US').format(n);
export function calculateMetrics(orders:Order[]):Metrics{
  const byLocation:Record<string,Metrics['locations'][number]>={};
  for(const o of orders){const p=byLocation[o.location_id]??={location_id:o.location_id,provider:o.provider,orders:0,net_sales_minor:0,discounts_minor:0,refunds_minor:0};p.orders++;p.net_sales_minor+=o.net_sales_minor;p.discounts_minor+=o.discount_minor;p.refunds_minor+=o.refund_minor}
  return {order_count:orders.length,net_sales_minor:orders.reduce((s,o)=>s+o.net_sales_minor,0),discounts_minor:orders.reduce((s,o)=>s+o.discount_minor,0),refunds_minor:orders.reduce((s,o)=>s+o.refund_minor,0),average_order_minor:orders.length?Math.round(orders.reduce((s,o)=>s+o.net_sales_minor,0)/orders.length):0,orders,locations:Object.values(byLocation).sort((a,b)=>a.location_id.localeCompare(b.location_id))}
}
