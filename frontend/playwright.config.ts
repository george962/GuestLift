import {defineConfig,devices} from '@playwright/test';

export default defineConfig({
 testDir:'./e2e',
 timeout:45_000,
 expect:{timeout:10_000},
 use:{...devices['Desktop Chrome'],baseURL:'http://localhost:3000',trace:'retain-on-failure'},
 reporter:'list',
 workers:1,
});
