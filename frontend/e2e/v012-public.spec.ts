/** Browser-level regression tests for v0.12 public preview. No merchant connections or charges. */
import {test, expect} from '@playwright/test';

test('public home explains the business workflow and labels samples', async ({page})=>{
 await page.goto('/');
 await expect(page.getByRole('heading',{name:/Know what matters/i})).toBeVisible();
 await expect(page.getByText(/fictional business without an account/i)).toBeVisible();
 await expect(page.getByText(/Production connections and billing are not enabled/i)).toBeVisible();
 await expect(page.getByText(/Open TableSignal/i)).toBeVisible();
});

test('finding investigation swaps evidence and uncertainty',async ({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:/Why are fewer identifiable guests returning/i}).click();
 await expect(page.getByRole('heading',{name:/Why are fewer identifiable guests returning/i})).toBeVisible();
 await expect(page.getByText(/Anonymous transactions cannot be assigned/i)).toBeVisible();
 await page.getByRole('button',{name:/What would this use in a real restaurant/i}).click();
 await expect(page.getByText(/permissioned POS order and discount records/i)).toBeVisible();
});

test('verified location count and selected amount are distinct',async ({page})=>{
 await page.goto('/');
 const pricing=page.locator('#pricing');
 await expect(pricing.getByText('Detected locations')).toBeVisible();
 await expect(pricing.getByText('Eligible in this example')).toBeVisible();
 await expect(pricing.getByText('$297')).toBeVisible();
 await pricing.getByLabel(/Midtown/i).check();
 await expect(pricing.getByText('$396')).toBeVisible();
 await expect(pricing.getByText('Review needed')).toBeVisible();
 await expect(pricing.locator('input[type=checkbox]:disabled')).toHaveCount(1);
});
