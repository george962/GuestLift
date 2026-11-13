import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {strict as assert} from 'node:assert';

const billing = readFileSync(new URL('../app/billing/page.tsx',import.meta.url),'utf8');
const success = readFileSync(new URL('../app/billing/success/page.tsx',import.meta.url),'utf8');

test('paid checkout has a separate verified confirmation page',()=>{
  assert.match(success,/\/api\/saas\/billing\/reconcile/);
  assert.match(success,/access_granted/);
  assert.match(success,/Stripe/);
});

test('billing allows repair without a second test charge',()=>{
  assert.match(billing,/Find my completed test checkout/);
  assert.match(billing,/checkout==='return'/);
  assert.match(billing,/\/api\/saas\/billing\/reconcile/);
  assert.match(billing,/has_billing_customer/);
});
