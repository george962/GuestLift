import test from 'node:test';import assert from 'node:assert/strict';
import {summarizeWorkspace,askWorkspace,discoverPatterns} from '../lib/workspace-analytics.mjs';
const orders=[
 {provider:'toast',source_order_id:'A',location_id:'L1',created_at:'2026-11-01',status:'PAID',customer_id:'C1',net_sales_minor:1500,discount_minor:200},
 {provider:'toast',source_order_id:'B',location_id:'L1',created_at:'2026-11-02',status:'PAID',customer_id:'C1',net_sales_minor:2000,discount_minor:100},
 {provider:'square',source_order_id:'C',location_id:'L2',created_at:'2026-11-02',status:'PAID',customer_id:null,net_sales_minor:500,discount_minor:0},
 {provider:'square',source_order_id:'D',location_id:'L2',created_at:'2026-11-02',status:'VOIDED',customer_id:'C2',net_sales_minor:9000,discount_minor:0},
];
const c=[{name:'Lunch offer',code:'LUNCH',redeemed_orders:2,attributed_net_sales_minor:3500,recorded_discount_minor:300,modeled_contribution_minor:100}];
test('summary tracks actual normalized net sales and ignores voids',()=>{const s=summarizeWorkspace(orders,c);assert.equal(s.orders,3);assert.equal(s.net_sales_minor,4000);assert.equal(s.discount_minor,300);assert.equal(s.repeat_customers,1);assert.equal(s.identified_customers,1);assert.equal(s.anonymous_orders,1)});
test('analyst uses evidence keys not fabricated causal claims',()=>{const s=summarizeWorkspace(orders,c);for(const q of ['why are customers returning','compare locations','coupon cost','show revenue']){const a=askWorkspace(q,s);assert.equal(a.causal_claim,false);assert.ok(a.evidence_keys.length);assert.ok(a.answer.length>30)}});
test('same customer ID across providers not automatically stitched',()=>{const s=summarizeWorkspace([{...orders[0]},{...orders[0],provider:'square',source_order_id:'X'}]);assert.equal(s.repeat_customers,0);assert.equal(s.identified_customers,2)});

test('pattern cards carry evidence keys and are derived from actual data',()=>{const s=summarizeWorkspace(orders,c);const signals=discoverPatterns(s);assert.ok(signals.length);assert.ok(signals[0].evidence_keys.length);assert.ok(signals.every(x=>!x.detail.includes('incremental profit')))});
