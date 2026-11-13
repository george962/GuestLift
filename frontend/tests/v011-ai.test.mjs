import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read = p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('AI analyst is visible in private navigation and has grounded graph + chat',()=>{
 const nav=read('components/site.tsx');
 const ui=read('app/analyst/page.tsx');
 assert.match(nav,/href:'\/analyst',label:'AI analyst'/);
 for(const name of ['/api/intelligence/brief','/api/intelligence/ask','brief.nodes','brief.edges','suggested_questions','model_configured','accountApi']){
  assert.ok(ui.includes(name),name);
 }
 assert.match(ui,/disabled=\{!brief.ai_ready/);
});

test('Pricing is explicit about free, commercial target and blocked real purchases',()=>{
 const pricing=read('app/pricing/page.tsx');
 assert.match(pricing,/\$99/);
 assert.match(pricing,/\$0/);
 assert.match(pricing,/Production sign-ups are not enabled yet/);
 assert.match(pricing,/not live yet/i);
 assert.doesNotMatch(pricing,/Start paid subscription now/i);
});

test('Connections do not offer fake production authorization',()=>{
 const connections=read('app/connections/page.tsx');
 assert.match(connections,/Production connection not yet active/);
 assert.match(connections,/Square Sandbox/);
 assert.match(connections,/Toast/);
});
