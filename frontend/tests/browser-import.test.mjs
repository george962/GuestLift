import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {transformUploaded,parseCsv,DEMO_FILES} from '../lib/browser-import.mjs';

const root=join(import.meta.dirname,'../../backend/fixtures');
function fixtures(provider){return Object.fromEntries(DEMO_FILES[provider].map(f=>[f,readFileSync(join(root,provider,f),'utf8')]))}

test('RFC4180 double quotes, commas and line feeds',()=>{
  const r=parseCsv('id,name\r\n1,"hello, world"\r\n2,"first\nsecond"\r\n3,"say ""Hi"""\r\n');
  assert.deepEqual(r,[{id:'1',name:'hello, world'},{id:'2',name:'first\nsecond'},{id:'3',name:'say "Hi"'}]);
});
test('Toast actual fixture files normalize and reconcile',()=>{
  const result=transformUploaded('toast',fixtures('toast'));
  assert.equal(result.summary.orders,28);
  assert.equal(result.summary.net_sales_minor,59470);
  assert.ok(result.records.some(r=>r.payments.length===2));
  assert.ok(result.records.every(o=>o.net_sales_minor===o.gross_minor-o.discount_minor-o.refund_minor));
});
test('Square fixture normalizes to same entity shape',()=>{
  const result=transformUploaded('square',fixtures('square'));
  assert.equal(result.summary.orders,28);
  assert.equal(result.summary.net_sales_minor,65080);
  assert.ok(result.records.every(o=>o.items.length>=1&&o.provider==='square'));
});
test('wrong file names and malformed amounts fail with helpful errors',()=>{
  const missing=fixtures('toast');delete missing['PaymentDetails.csv'];
  assert.throws(()=>transformUploaded('toast',missing),/Missing: PaymentDetails.csv/);
  const bad=fixtures('toast');bad['OrderDetails.csv']=bad['OrderDetails.csv'].replace('Order Id,','Wrong Name,');
  assert.throws(()=>transformUploaded('toast',bad),/missing required column: Order Id/);
  const badMoney=fixtures('toast');badMoney['OrderDetails.csv']=badMoney['OrderDetails.csv'].replace('1.50,1.73','bad,1.73');
  assert.throws(()=>transformUploaded('toast',badMoney),/expected a nonnegative dollar amount/);
});
test('duplicate CSV orders and orphaned item references fail',()=>{
  const duplicates=fixtures('toast');const lines=duplicates['OrderDetails.csv'].trimEnd().split('\n');duplicates['OrderDetails.csv']+='\n'+lines[1]+'\n';
  assert.throws(()=>transformUploaded('toast',duplicates),/duplicate Order Id/);
  const orphan=fixtures('toast');orphan['ItemSelectionDetails.csv']=orphan['ItemSelectionDetails.csv'].replace('9100001,91000011','wrong-order,91000011');
  assert.throws(()=>transformUploaded('toast',orphan),/Orphan item/);
});
test('Square unsupported currency and missing payment link fail',()=>{
  const wrong=fixtures('square');wrong['orders.json']=wrong['orders.json'].replace('"currency": "USD"','"currency": "EUR"');
  assert.throws(()=>transformUploaded('square',wrong),/expected USD/);
  const broken=fixtures('square');broken['refunds.json']=broken['refunds.json'].replace('"payment_id": "sq-payment-0007"','"payment_id": "does-not-exist"');
  assert.throws(()=>transformUploaded('square',broken),/references missing payment/);
});

test('fictional customer identity is optional and preserved across provider adapters',()=>{
  const toast=transformUploaded('toast',fixtures('toast')).records;
  const square=transformUploaded('square',fixtures('square')).records;
  assert.ok(toast.some(o=>o.customer_id?.startsWith('TEST-TOAST-')));
  assert.ok(square.some(o=>o.customer_id?.startsWith('TEST-SQUARE-')));
  assert.ok(toast.some(o=>o.customer_id==null));
  assert.ok(square.some(o=>o.customer_id==null));
});
