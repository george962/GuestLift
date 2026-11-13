/** Read-only, deterministic insight tools on the SAME fictional orders as existing GuestLift. */
export function summarizeWorkspace(orders, campaigns=[]) {
  const valid=orders.filter(o=>!['VOIDED','CANCELED','CANCELLED'].includes(String(o.status).toUpperCase()));
  const total=valid.reduce((s,o)=>s+Number(o.net_sales_minor||0),0);
  const discounts=valid.reduce((s,o)=>s+Number(o.discount_minor||0),0);
  const customerCounts=new Map(), locs=new Map(), days=new Map();
  let identified=0;
  for(const o of valid){
    const k=`${o.provider}:${o.location_id}`;
    const loc=locs.get(k)||{location:k,orders:0,net_sales_minor:0,discount_minor:0};
    loc.orders++;loc.net_sales_minor+=o.net_sales_minor;loc.discount_minor+=o.discount_minor;locs.set(k,loc);
    const d=String(o.created_at||'').slice(0,10);
    if(d){const day=days.get(d)||{date:d,orders:0,net_sales_minor:0};day.orders++;day.net_sales_minor+=o.net_sales_minor;days.set(d,day)}
    if(o.customer_id){identified++;const id=`${o.provider}:${o.customer_id}`;customerCounts.set(id,(customerCounts.get(id)||0)+1)}
  }
  const repeats=[...customerCounts.values()].filter(n=>n>=2).length;
  const campaignRows=campaigns.map(c=>({
    code:c.code,name:c.name,redemptions:c.redeemed_orders,
    net_sales_minor:c.attributed_net_sales_minor,discount_minor:c.recorded_discount_minor,
    modeled_contribution_minor:c.modeled_contribution_minor
  }));
  return {orders:valid.length,net_sales_minor:total,discount_minor:discounts,
    average_order_minor:valid.length?Math.round(total/valid.length):0,
    identified_orders:identified,identified_customers:customerCounts.size,repeat_customers:repeats,
    identification_coverage_percent:valid.length?Math.round(1000*identified/valid.length)/10:0,
    repeat_customer_rate_percent:customerCounts.size?Math.round(1000*repeats/customerCounts.size)/10:null,
    anonymous_orders:valid.length-identified,
    locations:[...locs.values()].sort((a,b)=>b.net_sales_minor-a.net_sales_minor),
    daily:[...days.values()].sort((a,b)=>a.date.localeCompare(b.date)),campaigns:campaignRows,
    data_origin:'fictional_browser_orders'};
}
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
export function askWorkspace(question, summary){
  const q=String(question||'').trim().toLowerCase();if(!q)throw new Error('Enter a question');
  let answer,tool,evidence,next;
  if(/customer|repeat|return|retention|loyal|lapse/.test(q)){
    answer=summary.identified_customers?`${summary.repeat_customers} of ${summary.identified_customers} identified fictional customers purchased at least twice (${summary.repeat_customer_rate_percent}%). Only ${summary.identification_coverage_percent}% of orders carry usable IDs. This is observed behavior, not proof that a promotion caused retention.`:'Customer identifiers are missing; no reliable repeat-customer rate is available.';
    tool='customer_repeat';evidence=['identified_customers','repeat_customers','repeat_customer_rate_percent','identification_coverage_percent'];next='Compare equal historical windows when available.';
  }else if(/campaign|promotion|coupon|discount|offer/.test(q)){
    const n=summary.campaigns.reduce((s,c)=>s+c.redemptions,0),discount=summary.campaigns.reduce((s,c)=>s+c.discount_minor,0);
    answer=`We matched ${n} synthetic coupon redemptions across ${summary.campaigns.length} campaigns, with ${money(discount)} in recorded campaign discounts. These attributed orders do not establish incremental revenue or ROI.`;
    tool='coupon_economics';evidence=['campaigns','discount_minor'];next='Test the next promotion with a randomized holdout.';
  }else if(/location|store|branch|best|worst/.test(q)){
    const best=summary.locations[0];answer=best?`${best.location} has the most observed net sales (${money(best.net_sales_minor)} from ${best.orders} fictional orders). Locations may differ in hours and traffic; this is not an adjusted performance ranking.`:'No store data is available.';
    tool='location_compare';evidence=['locations'];next='Compare locations after normalizing for comparable operating periods.';
  }else{
    answer=`This fictional dataset contains ${summary.orders} orders and ${money(summary.net_sales_minor)} net sales, averaging ${money(summary.average_order_minor)} per order. I cannot infer why sales changed without a suitable comparison period.`;
    tool='sales_overview';evidence=['orders','net_sales_minor','average_order_minor'];next='Ask about promotions, customer repeat purchasing or locations.';
  }
  return {answer,tool,evidence_keys:evidence,recommended_next_step:next,engine:'verified_rules',data_origin:'synthetic',causal_claim:false};
}

/** Transparent signals; descriptive flags, never predictive or causal claims. */
export function discoverPatterns(summary){
 const signals=[];
 if(summary.orders>=10 && summary.identification_coverage_percent<80){
  signals.push({id:'identity_coverage',level:'investigate',title:'Customer identity coverage is limited',
   detail:`Only ${summary.identification_coverage_percent}% of orders have a usable customer ID. Repeat-customer analysis excludes the remaining orders.`,
   evidence_keys:['identified_orders','orders','identification_coverage_percent'],question:'What do we know about returning customers?'});
 }
 if(summary.net_sales_minor>0 && summary.discount_minor/summary.net_sales_minor>.08){
  signals.push({id:'discount_share',level:'investigate',title:'Discount exposure is worth reviewing',
   detail:`Recorded discounts equal ${(summary.discount_minor/summary.net_sales_minor*100).toFixed(1)}% of observed net sales. This ratio is descriptive, not a profit estimate.`,
   evidence_keys:['discount_minor','net_sales_minor'],question:'Which campaign gave the most discounts?'});
 }
 if(summary.locations.length>=2){
  const high=Math.max(...summary.locations.map(x=>x.net_sales_minor)),low=Math.min(...summary.locations.map(x=>x.net_sales_minor));
  if(low>0&&high/low>=1.5)signals.push({id:'location_variation',level:'context',title:'Location sales vary across the sample',
   detail:`The highest location has ${(high/low).toFixed(1)}× the observed net sales of the lowest. Store size, hours and traffic may explain part of the difference.`,
   evidence_keys:['locations'],question:'Which restaurant location has the most sales?'});
 }
 if(!signals.length)signals.push({id:'none',level:'context',title:'No flagged patterns at this sample size',detail:'Continue collecting comparable data; no anomaly or causality conclusion is warranted.',evidence_keys:['orders','locations'],question:'Summarize my sales'});
 return signals;
}
