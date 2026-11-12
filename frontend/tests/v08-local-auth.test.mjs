import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
const base=resolve(import.meta.dirname,'..');
const read=p=>readFileSync(resolve(base,p),'utf8');
test('v0.8 uses local DB session cookies rather than Supabase or browser-held auth secrets',()=>{
 const client=read('lib/local-auth.ts');
 for(const key of ['credentials:\'include\'','/api/local-auth/login','/api/local-auth/register','/api/local-auth/session','/api/local-auth/logout','X-CSRF-Token'])assert.ok(client.includes(key),key);
 assert.doesNotMatch(client,/localStorage|sessionStorage|Bearer /);
 assert.ok(existsSync(resolve(base,'lib/supabase-client.ts')));
 assert.match(read('lib/supabase-client.ts'),/from '\.\/local-auth'/);
 assert.doesNotMatch(read('package.json'),/@supabase/);
});
test('local accounts support registration, settings, password change and test billing',()=>{
 const auth=read('components/auth-panel.tsx');
 for(const k of ['signUp','signInWithPassword','currentPassword','updateUser','safeNext'])assert.ok(auth.includes(k));
 assert.match(read('app/account/page.tsx'),/\/reset-password/);
 assert.match(read('app/onboarding/page.tsx'),/\/billing/);
 assert.match(read('app/billing/page.tsx'),/\/api\/saas\/billing/);
});
