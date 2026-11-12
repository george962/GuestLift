import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
const root=resolve(import.meta.dirname,'..');
const read=p=>readFileSync(resolve(root,p),'utf8');
test('v0.6 has dedicated account and billing management screens',()=>{
 for(const p of ['app/sign-in/page.tsx','app/sign-up/page.tsx','app/forgot-password/page.tsx','app/reset-password/page.tsx','app/onboarding/page.tsx','app/settings/page.tsx','app/billing/page.tsx','app/pricing/page.tsx','app/help/page.tsx','app/connect/page.tsx'])assert.ok(existsSync(resolve(root,p)),p);
 assert.match(read('components/auth-panel.tsx'),/resetPasswordForEmail/);
 assert.match(read('components/auth-panel.tsx'),/signInWithPassword/);
 assert.match(read('components/auth-panel.tsx'),/signUp/);
 assert.match(read('app/billing/page.tsx'),/\/api\/saas\/billing\//);
});
test('homepage motion tour offers pause, manual controls and reduced-motion behavior',()=>{
 const tour=read('components/motion-tour.tsx'), css=read('app/globals.css');
 assert.match(tour,/setInterval/);assert.match(tour,/setPlaying/);assert.match(tour,/prefers-reduced-motion/);
 assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
});
test('operator workspace has exactly four primary task tabs',()=>{
 const s=read('app/workspace/page.tsx');
 const m=s.match(/const menu:\[Page,string,typeof LayoutDashboard\]\[\]=\[([\s\S]*?)\];/);assert.ok(m,'menu definition');
 assert.equal((m[1].match(/\['(?:overview|customers|campaigns|analyst)'/g)||[]).length,4);
 assert.match(s,/href="\/billing"/);assert.match(s,/href="\/connect"/);
});
