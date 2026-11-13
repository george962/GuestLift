import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
const base=resolve(import.meta.dirname,'..');
const read=p=>readFileSync(resolve(base,p),'utf8');
test('expanded landing reuses canonical computed metrics rather than hard-coded sales promises',()=>{
 const s=read('components/landing-experience.tsx');
 for(const snippet of ['summarizeWorkspace','evaluateCampaigns','askWorkspace','MotionTour','v7-marquee','StoryFlow','AskPreview','useReveal'])assert.match(s,new RegExp(snippet));
 assert.match(s,/fictional data/i);assert.match(s,/No account required/i);
 assert.doesNotMatch(s,/guaranteed ROI|guaranteed profit/i);
});
test('website exposes local sign-in and server-mediated Stripe TEST subscription journey',()=>{
 const auth=read('components/auth-panel.tsx'),billing=read('app/billing/page.tsx'),navbar=read('components/site.tsx');
 for(const snippet of ['signUp','signInWithPassword','updateUser','safeNext','currentPassword'])assert.ok(auth.includes(snippet));
 for(const snippet of ['/api/saas/billing/','/api/saas/config','checkout','portal','subscription_status'])assert.ok(billing.includes(snippet));
 assert.match(navbar,/onAuthStateChange/);
 assert.match(read('app/pricing/page.tsx'),/Production sign-ups are not enabled yet/);
 assert.match(read('app/onboarding/page.tsx'),/\/billing/);
});
test('animations and the page respect motion preferences and support keyboard interaction',()=>{
 const s=read('components/landing-experience.tsx'),css=read('app/globals.css');
 assert.match(s,/IntersectionObserver/);assert.match(s,/aria-pressed=/);
 assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
 assert.match(css,/@keyframes v7-marquee-move/);
 for(const p of ['app/sign-in/page.tsx','app/sign-up/page.tsx','app/account/page.tsx','app/billing/page.tsx','app/forgot-password/page.tsx','app/reset-password/page.tsx','app/onboarding/page.tsx'])assert.ok(existsSync(resolve(base,p)),p);
});
