/**
 * M1 golden-path journey (docs/PRODUCT_PLAN.md, steps 2–7) against the mock Square API.
 * Run locally with scripts/journey.sh; CI runs it in the `journey` job.
 */
import {expect, test, type Page} from '@playwright/test';
import {setupClerkTestingToken} from '@clerk/testing/playwright';

const MOCK = process.env.MOCK_SQUARE_URL || 'http://localhost:8100';
const CLERK = process.env.JOURNEY_AUTH_MODE === 'clerk';
const PASSWORD = 'journey-Pw-' + Math.random().toString(36).slice(2, 10) + '-7Qz!';

async function signUp(page: Page, email: string) {
  if (!CLERK) {
    await page.goto('/sign-up');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', {exact: true}).fill(PASSWORD);
    await page.getByLabel('Confirm password').fill(PASSWORD);
    await page.getByRole('button', {name: /Create account/}).click();
    return;
  }
  // Real Clerk development instance. "+clerk_test" emails accept the fixed code 424242 and send no mail.
  await setupClerkTestingToken({page});
  await page.goto('/sign-up');
  await page.getByLabel(/Email address/i).fill(email);
  await page.getByLabel(/^Password/i).fill(PASSWORD);
  await page.getByRole('button', {name: /^Continue$/}).click();
  await page.getByLabel(/Enter verification code|Verification code/i).first().waitFor();
  await page.keyboard.type('424242');
  // If the Clerk instance still requires organizations, get past that screen (owner should turn it off).
  const orgTask = page.getByRole('heading', {name: /Setup your organization/i});
  const welcome = page.getByRole('heading', {name: 'Your TableSignal account is ready.'});
  await expect(orgTask.or(welcome)).toBeVisible({timeout: 20_000});
  if (await orgTask.isVisible()) {
    console.warn('Clerk instance requires organizations; disable "membership required" in the Clerk dashboard.');
    await page.getByRole('button', {name: /^Continue$/}).click();
  }
}

test('owner signs up, connects Square, syncs, reads the brief and saves a decision', async ({page, request}) => {
  test.setTimeout(120_000);
  const truth = await (await request.get(`${MOCK}/__mock/truth`)).json();
  const email = CLERK ? `journey${Date.now()}+clerk_test@example.com` : `owner+${Date.now()}@harbor.test`;

  await test.step('2 · sign up and land in onboarding', async () => {
    await signUp(page, email);
    await expect(page.getByRole('heading', {name: 'Your TableSignal account is ready.'})).toBeVisible({timeout: 20_000});
    // Regression (CI, PR #29): the first account load finishing after the save sent the owner back to step 1.
    await page.route('**/api/saas/me', async route => {
      if (route.request().method() === 'GET') await new Promise(r => setTimeout(r, 2500));
      await route.continue().catch(() => {});  // the page may have moved on while we waited
    });
    const slowProgress = page.waitForResponse(r => r.url().includes('/api/saas/me') && r.request().method() === 'GET');
    await page.getByRole('link', {name: /Set up my restaurant/}).click();
    await page.getByLabel('Restaurant name').fill('Harbor Café');
    await page.getByRole('button', {name: /Save and continue/}).click();
    await slowProgress;  // the stale load lands after the save, as it did in CI
    await page.getByRole('button', {name: /Continue free/}).click();
    await page.unroute('**/api/saas/me');
    await expect(page.getByText('Next: connect your orders.')).toBeVisible();
  });

  await test.step('3 · connect Square via OAuth and select eligible locations', async () => {
    await page.getByRole('link', {name: /Connect Square Sandbox/}).click();
    await page.getByRole('button', {name: /Authorize with Square Sandbox/}).click();
    await page.waitForURL(/\/connections\?square=connected/);
    for (const id of truth.eligible_location_ids) {
      const box = page.locator('label', {hasText: id === 'LOC_HARBOR' ? 'Harbor Street' : 'Market Square'}).getByRole('checkbox');
      await box.check();
    }
    await expect(page.locator('label', {hasText: 'Online Store'}).getByRole('checkbox')).toBeDisabled();
    await page.getByRole('button', {name: /Save monitored Sandbox locations/}).click();
    await expect(page.getByText(`Saved: ${truth.eligible_location_ids.length}`)).toBeVisible();
  });

  await test.step('4 · sync and see the import result', async () => {
    await page.getByRole('button', {name: /Sync now/}).click();
    await expect(page.getByText(`Sync complete: ${truth.importable_orders} new`)).toBeVisible({timeout: 30_000});
  });

  await test.step('M3 · "Check against Square" matches Square for each location', async () => {
    // Same default range as the page: the 7 days ending yesterday (UTC calendar).
    const now = new Date();
    const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - 1));
    const days = [...Array(7)].map((_, i) => new Date(end.getTime() - i * 864e5).toISOString().slice(0, 10));
    const money = (n: number) => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(n / 100);
    for (const loc of truth.eligible_location_ids as string[]) {
      const net = days.reduce((sum, d) => sum + (truth.daily[loc]?.[d]?.net_sales_minor ?? 0), 0);
      await expect(page.locator(`tr[data-location="${loc}"] td[data-col="net_sales_minor"]`)).toHaveText(money(net));
    }
    await expect(page.getByText('Up to date')).toBeVisible();
  });

  await test.step('M5 · the first complete sync starts the 14-day no-card trial', async () => {
    await page.goto('/billing');
    const plan = page.locator('[data-plan="trial"]').first();
    await expect(plan).toContainText('Free trial');
    await expect(plan).toContainText('14 days left');
  });

  await test.step('M5 · changing locations shows the price first, then saves', async () => {
    await page.getByLabel('Market Square').uncheck();
    await page.getByRole('button', {name: 'Preview the price'}).click();
    const preview = page.locator('[data-preview]');
    await expect(preview).toContainText('2 → 1 location');
    await expect(preview).toContainText('Nothing is charged until you subscribe');
    await page.getByRole('button', {name: 'Confirm change'}).click();
    await expect(page.getByText('Locations updated.')).toBeVisible();
    await page.getByLabel('Market Square').check();   // put it back for the steps below
    await page.getByRole('button', {name: 'Preview the price'}).click();
    await page.getByRole('button', {name: 'Confirm change'}).click();
    await expect(page.getByText('Locations updated.')).toBeVisible();
    // Re-adding a location queues its history import; the background worker brings the numbers back.
    const orders = new Intl.NumberFormat('en-US').format(truth.completed_orders);
    await expect(async () => {
      await page.goto('/dashboard');
      await expect(page.locator('.ts9-metric', {hasText: 'Completed orders'})).toContainText(orders, {timeout: 2_000});
    }).toPass({timeout: 45_000});
  });

  await test.step('5 · the dashboard shows numbers that match Square', async () => {
    await page.goto('/dashboard');
    const orders = new Intl.NumberFormat('en-US').format(truth.completed_orders);
    await expect(page.locator('.ts9-metric', {hasText: 'Completed orders'})).toContainText(orders);
  });

  await test.step('6 · the weekly brief shows the planted Market Square dip, with evidence', async () => {
    await page.goto('/analyst');
    const brief = page.locator('[data-weekly-brief]');
    await expect(brief).toContainText(truth.planted.market_weekday_dip_week);
    await expect(brief.locator('[data-finding^="LOC_MARKET:"]').first()).toContainText(/Market Square: .* down \d+%/);
    await expect(page.locator('.ts11-findings article').first()).toBeVisible();
  });

  await test.step('7 · save a decision and find it in saved decisions', async () => {
    await page.goto('/opportunities');
    await page.getByLabel('Decision title').fill('Win back lapsed regulars');
    await page.getByLabel('What to measure').selectOption('orders');
    await page.getByLabel('Where').selectOption('LOC_HARBOR');
    // Logged after the fact: the change started 5 weeks ago, so its 4-week readout is already due.
    const started = new Date(Date.now() - 35 * 864e5).toISOString().slice(0, 10);
    await page.getByLabel('The change starts (or started) on').fill(started);
    await page.getByRole('button', {name: /^Save/}).click();
    await expect(page.getByText('Draft saved.')).toBeVisible();
    await page.getByRole('link', {name: /Review your saved decisions/}).click();
    await expect(page.getByText('Win back lapsed regulars')).toBeVisible();
  });

  await test.step('9 · the outcome readout finds the planted weekend lift, without claiming a cause', async () => {
    const readout = page.locator('[data-outcome="clear"], [data-outcome="possible"]').first();
    await expect(readout).toContainText('after the change');
    await expect(readout).toContainText('not proof that it caused');
  });

  await test.step('M2 · the owner deletes the workspace and the account', async () => {
    await page.goto('/settings');
    await page.getByLabel(/Type .* to confirm/).fill('Harbor Café');
    await page.getByRole('button', {name: 'Delete workspace and account'}).click();
    await page.waitForURL(/\/\?deleted=1/);
    await page.goto('/dashboard');
    await expect(page.getByRole('link', {name: /Sign in/}).first()).toBeVisible();
  });
});
