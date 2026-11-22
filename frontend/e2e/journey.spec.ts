/**
 * M1 golden-path journey (docs/PRODUCT_PLAN.md, steps 2–7) against the mock Square API.
 * Run locally with scripts/journey.sh; CI runs it in the `journey` job.
 */
import {expect, test} from '@playwright/test';

const MOCK = process.env.MOCK_SQUARE_URL || 'http://localhost:8100';

test('owner signs up, connects Square, syncs, reads the brief and saves a decision', async ({page, request}) => {
  test.setTimeout(120_000);
  const truth = await (await request.get(`${MOCK}/__mock/truth`)).json();
  const email = `owner+${Date.now()}@harbor.test`;

  await test.step('2 · sign up and land in onboarding', async () => {
    await page.goto('/sign-up');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', {exact: true}).fill('a-long-journey-password');
    await page.getByLabel('Confirm password').fill('a-long-journey-password');
    await page.getByRole('button', {name: /Create account/}).click();
    await expect(page.getByRole('heading', {name: 'Your TableSignal account is ready.'})).toBeVisible();
    await page.getByRole('link', {name: /Set up my restaurant/}).click();
    await page.getByLabel('Restaurant name').fill('Harbor Café');
    await page.getByRole('button', {name: /Save and continue/}).click();
    await page.getByRole('button', {name: /Continue free/}).click();
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
    await page.getByRole('button', {name: /Sync last 180 days/}).click();
    await expect(page.getByText(`Sync complete: ${truth.importable_orders} new`)).toBeVisible({timeout: 30_000});
  });

  await test.step('5 · the dashboard shows numbers that match Square', async () => {
    await page.goto('/dashboard');
    const orders = new Intl.NumberFormat('en-US').format(truth.completed_orders);
    await expect(page.locator('.ts9-metric', {hasText: 'Completed orders'})).toContainText(orders);
  });

  await test.step('6 · the brief renders evidence and findings', async () => {
    await page.goto('/analyst');
    await expect(page.locator('.ts11-findings article').first()).toBeVisible();
  });

  await test.step('7 · save a decision and find it in saved decisions', async () => {
    await page.goto('/opportunities');
    await page.getByLabel('Decision title').fill('Win back lapsed regulars');
    await page.getByRole('button', {name: /^Save/}).click();
    await expect(page.getByText('Draft saved.')).toBeVisible();
    await page.getByRole('link', {name: /Review your saved decisions/}).click();
    await expect(page.getByText('Win back lapsed regulars')).toBeVisible();
  });
});
