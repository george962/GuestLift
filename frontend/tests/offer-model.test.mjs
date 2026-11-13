import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluateOffer} from '../lib/offer-model.mjs';
const orders=[
  {provider:'toast',source_order_id:'a',location_id:'L1',net_sales_minor:2000,status:'CLOSED'},
  {provider:'square',source_order_id:'b',location_id:'L2',net_sales_minor:800,status:'COMPLETED'},
];
const base={type:'percent',minimumMinor:1500,value:10,amountMinor:0,marginPercent:40};
test('percentage offer only applies to eligible orders',()=>{
 const r=evaluateOffer(orders,base);
 assert.equal(r.eligibleCount,1);
 assert.equal(r.additionalDiscountMinor,200);
 assert.equal(r.modeledNetMinor,2600);
 assert.equal(r.baseContributionMinor,1120);
 assert.equal(r.scenarioContributionMinor,920);
 assert.equal(r.breakEvenAddedOrders,1);
});
test('fixed offer cannot exceed a basket',()=>{
 const r=evaluateOffer(orders,{...base,type:'fixed',amountMinor:6000,minimumMinor:0});
 assert.equal(r.additionalDiscountMinor,2800);
 assert.equal(r.modeledNetMinor,0);
 assert.equal(r.breakEvenAddedOrders,null);
});
test('free item affects contribution but not net sales',()=>{
 const r=evaluateOffer(orders,{...base,type:'free_item',amountMinor:250});
 assert.equal(r.additionalDiscountMinor,0);
 assert.equal(r.rewardCostMinor,250);
 assert.equal(r.modeledNetMinor,2800);
 assert.equal(r.scenarioContributionMinor,870);
});
test('no matching transactions are handled',()=>{
 const r=evaluateOffer(orders,{...base,minimumMinor:10000});
 assert.equal(r.eligibleCount,0);
 assert.equal(r.offerCostMinor,0);
 assert.equal(r.breakEvenAddedOrders,0);
});
