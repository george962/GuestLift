import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
const root=resolve(import.meta.dirname,'..');
const read=p=>readFileSync(resolve(root,p),'utf8');

test('private navigation organizes the product around tasks, not developer setup',()=>{
 const nav=read('components/site.tsx');
 for(const tab of ['Overview','Guests','Opportunities','Experiments'])assert.ok(nav.includes(tab));
 for(const route of ['/dashboard','/guests','/opportunities','/experiments'])assert.ok(nav.includes(route));
 assert.ok(nav.includes('Subscription & billing'));
});
test('signup confirmation, persistent onboarding and private routes exist',()=>{
 assert.ok(existsSync(resolve(root,'app/account/welcome/page.tsx')));
 assert.match(read('components/auth-panel.tsx'),/\/account\/welcome/);
 assert.match(read('app/onboarding/page.tsx'),/\/api\/saas\/onboarding/);
 assert.ok(read('lib/local-auth.ts').includes('for(let attempt=0;attempt<3;attempt++)'));
});
test('offers create a saved account-scoped experiment, no unsupported send action',()=>{
 const page=read('app/opportunities/page.tsx');
 assert.match(page,/\/api\/decisions\/opportunities/);
 assert.match(page,/\/api\/decisions\/plans/);
 assert.match(page,/Not incremental profit/);
 assert.doesNotMatch(page,/sendCampaign|sendEmail|sendSms/);
 const experiments=read('app/experiments/page.tsx');
 assert.match(experiments,/\/api\/decisions\/plans/);
 assert.match(experiments,/draft|planned|reviewed/);
});
