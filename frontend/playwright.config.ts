import {defineConfig,devices} from '@playwright/test';

export default defineConfig({
 testDir:'./e2e',
 globalSetup:process.env.JOURNEY_AUTH_MODE==='clerk'?'./e2e/clerk.global-setup.ts':undefined,
 timeout:45_000,
 expect:{timeout:10_000},
 use:{...devices['Desktop Chrome'],baseURL:process.env.JOURNEY_BASE_URL||'http://localhost:3000',trace:'retain-on-failure'},
 reporter:'list',
 workers:1,
});
