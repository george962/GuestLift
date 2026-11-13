import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
const root=resolve(import.meta.dirname,'..');
const read=p=>readFileSync(resolve(root,p),'utf8');

test('v0.9 has private no-fake-data dashboard and separate public demo',()=>{
  const d=read('components/private-dashboard.tsx');
  assert.match(d,/\/api\/saas\/me/);
  assert.match(d,/no connected data source|No connected data source/i);
  assert.match(d,/\/connections/);
  assert.doesNotMatch(d,/DEFAULT_ORDERS|demo-fallback.json|campaign-demo.json/);
  assert.ok(existsSync(resolve(root,'app/workspace/page.tsx')));
});

test('v0.10 onboarding persists restaurant, plan and provider connection stages',()=>{
  const onboarding=read('app/onboarding/page.tsx');
  for(const x of ['Restaurant','Plan','Connect data','/connections','/billing','/api/saas/onboarding'])assert.ok(onboarding.includes(x),x);
  assert.match(read('components/auth-panel.tsx'),/\/account\/welcome/);
  assert.match(read('components/site.tsx'),/My restaurant/);
});

test('v0.9 connection page uses server-side authenticated API and no browser token input',()=>{
  const connect=read('app/connections/page.tsx');
  for(const x of ['/api/integrations/square/','connect-developer-sandbox','oauth/start','assisted-setup','disconnect','sync'])assert.ok(connect.includes(x),x);
  assert.doesNotMatch(connect,/type="password"|SQUARE_SANDBOX_ACCESS_TOKEN.*value=/);
  assert.match(connect,/Sync last 180 days/);
});
