/**
 * Deterministic, browser-only campaign analysis for fictional records.
 * Identical business rules are also implemented in the local FastAPI/SQL demo.
 * Inputs NEVER leave the browser in static hosting mode.
 */
import {parseCsv} from './browser-import.mjs';
const CAMPAIGNS=['campaign_id','code','name','offer_type','start_date','end_date','variable_cost_minor','fixed_cost_minor','description'];
const REDEMPTIONS=['redemption_id','campaign_id','provider','source_order_id','redeemed_at','discount_minor'];
function fail(s){throw new Error(s)}
function required(s,f){const a=String(s??'').trim();if(!a)fail(`${f} is required`);if(a.length>160)fail(`${f} is too long`);return a}
function cents(s,f){const str=required(s,f);if(!/^\d{1,11}$/.test(str))fail(`${f}: expected nonnegative integer cents`);return Number(str)}
function rowsFor(text,fields,file){if(typeof text!=='string'||text.length>2_000_000)fail(`${file}: empty or too large`);const first=text.replace(/^\uFEFF/,'').split(/\r?\n/,1)[0].split(',');const missing=fields.filter(f=>!first.includes(f));if(missing.length)fail(`${file}: missing required columns: ${missing.join(', ')}`);const rows=parseCsv(text);if(rows.length>2000)fail(`${file}: maximum 2000 rows`);return rows}
function parseDate(s){const v=required(s,'date');if(!/^\d{4}-\d{2}-\d{2}$/.test(v)||Number.isNaN(Date.parse(v+'T00:00:00Z')))fail('Date must be valid YYYY-MM-DD');return v}
function campaign(row){const a={};for(const f of ['campaign_id','code','name','offer_type'])a[f]=required(row[f],f);a.start_date=parseDate(row.start_date);a.end_date=parseDate(row.end_date);if(a.end_date<a.start_date)fail('campaign end before start');if(!['percent','fixed','free_item','other'].includes(a.offer_type))fail('Unknown offer_type');a.variable_cost_minor=cents(row.variable_cost_minor,'variable_cost_minor');a.fixed_cost_minor=cents(row.fixed_cost_minor,'fixed_cost_minor');a.description=String(row.description??'');return a}
function redemption(row){const a={};for(const f of ['redemption_id','campaign_id','provider','source_order_id','redeemed_at'])a[f]=required(row[f],f);if(!['toast','square'].includes(a.provider))fail('provider must be toast or square');if(!/Z$|[+-]\d\d:\d\d$/.test(a.redeemed_at)||!Number.isFinite(Date.parse(a.redeemed_at)))fail('redeemed_at must include a timezone');a.discount_minor=cents(row.discount_minor,'discount_minor');return a}

export function repeatCustomerSummary(orders){
 const byId=new Map();let identified=0;
 for(const o of orders){if(!o.customer_id||['VOIDED','CANCELED'].includes(o.status))continue;identified++;const k=`${o.provider}:${o.customer_id}`;byId.set(k,(byId.get(k)||0)+1)}
 const repeats=[...byId.values()].filter(n=>n>=2).length;
 return {total_orders:orders.length,identified_orders:identified,identified_customers:byId.size,repeat_customers:repeats,
  customer_coverage_percent:orders.length?Math.round(identified/ orders.length*1000)/10:0,
  repeat_customer_rate_percent:byId.size?Math.round(repeats/byId.size*1000)/10:0,
  anonymous_orders:orders.length-identified};
}

export function evaluateCampaigns(orders,campaignsCsv,redemptionsCsv,marginPercent=35){
 const margin=Number(marginPercent);if(!Number.isInteger(margin)||margin<0||margin>95)fail('Margin assumption must be an integer 0–95');
 const campaignRows=rowsFor(campaignsCsv,CAMPAIGNS,'Campaigns.csv');
 const redemptionRows=rowsFor(redemptionsCsv,REDEMPTIONS,'Redemptions.csv');
 const issues=[],campaigns=[],cMap=new Map(),rMatches=[],seen=new Set(),occupied=new Set();
 for(const [index,row] of campaignRows.entries()){
  try{const item=campaign(row);if(cMap.has(item.campaign_id))fail(`duplicate campaign_id ${item.campaign_id}`);cMap.set(item.campaign_id,item);campaigns.push(item)}
  catch(e){issues.push(`Campaigns.csv row ${index+2}: ${e.message}`)}
 }
 const orderMap=new Map(orders.map(o=>[`${o.provider}:${o.source_order_id}`,o]));
 for(const [index,row] of redemptionRows.entries()){
  try{
   const item=redemption(row);if(seen.has(item.redemption_id))fail(`duplicate redemption ID ${item.redemption_id}`);
   seen.add(item.redemption_id);
   const c=cMap.get(item.campaign_id);if(!c)fail(`campaign ${item.campaign_id} not found`);
   const k=`${item.provider}:${item.source_order_id}`,o=orderMap.get(k);
   if(!o)fail(`order ${k} not found in chosen POS dataset`);
   if(['VOIDED','CANCELED'].includes(o.status))fail('voided order cannot redeem');
   if(item.redeemed_at.slice(0,10)<c.start_date||item.redeemed_at.slice(0,10)>c.end_date)fail('redemption outside campaign range');
   if(item.discount_minor>o.discount_minor)fail(`discount ${item.discount_minor} exceeds POS recorded discount ${o.discount_minor}`);
   if(occupied.has(k))fail('order already has a campaign redemption');
   occupied.add(k);rMatches.push({item,order:o});
  }catch(e){issues.push(`Redemptions.csv row ${index+2}: ${e.message}`)}
 }
 const counts=new Map();for(const o of orders){if(o.customer_id&&!['VOIDED','CANCELED'].includes(o.status)){const k=`${o.provider}:${o.customer_id}`;counts.set(k,(counts.get(k)||0)+1)}}
 const results=campaigns.map(c=>{
  const matches=rMatches.filter(x=>x.item.campaign_id===c.campaign_id);
  const sales=matches.reduce((s,x)=>s+x.order.net_sales_minor,0);
  const locations=new Map();
  for(const {item,order} of matches){const key=`${order.provider}:${order.location_id}`;
   const x=locations.get(key)??{provider:order.provider,location_id:order.location_id,redeemed_orders:0,net_sales_minor:0,recorded_discount_minor:0};
   x.redeemed_orders++;x.net_sales_minor+=order.net_sales_minor;x.recorded_discount_minor+=item.discount_minor;locations.set(key,x)}
  const redeemers=new Set(matches.filter(x=>x.order.customer_id).map(x=>`${x.order.provider}:${x.order.customer_id}`));
  return {...c,redeemed_orders:matches.length,attributed_net_sales_minor:sales,recorded_discount_minor:matches.reduce((s,x)=>s+x.item.discount_minor,0),
   recorded_refund_minor:matches.reduce((s,x)=>s+x.order.refund_minor,0),variable_campaign_cost_minor:matches.length*c.variable_cost_minor,
   fixed_campaign_cost_minor:c.fixed_cost_minor,modeled_contribution_minor:Math.round(sales*margin/100)-matches.length*c.variable_cost_minor-c.fixed_cost_minor,
   identified_redeemers:redeemers.size,repeat_redeemers:[...redeemers].filter(k=>(counts.get(k)||0)>=2).length,
   anonymous_redemptions:matches.filter(x=>!x.order.customer_id).length,
   locations:[...locations.values()].sort((a,b)=>a.provider.localeCompare(b.provider)||a.location_id.localeCompare(b.location_id)),
   order_matches:matches.map(({item,order})=>({redemption_id:item.redemption_id,provider:order.provider,source_order_id:order.source_order_id,
    location_id:order.location_id,customer_id:order.customer_id??null,net_sales_minor:order.net_sales_minor,recorded_discount_minor:item.discount_minor,
    refund_minor:order.refund_minor,redeemed_at:item.redeemed_at}))};
 });
 return {campaigns:results,margin_assumption_percent:margin,customer_summary:repeatCustomerSummary(orders),total_redemptions:rMatches.length,
  rejected:issues.length,issues,
  disclaimer:'Fictional dataset; attributed sales and assumed contribution are not causal lift. Discounts already reduce POS net sales.'};
}
