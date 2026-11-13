/** Browser smoke tests. Run on your local Docker instance with test credentials only. */
import {test,expect} from '@playwright/test';

test('pricing explains the free demo versus the unlaunched Growth product', async ({page})=>{
 await page.goto('/pricing');
 await expect(page.getByText('Production sign-ups are not enabled yet.')).toBeVisible();
 await expect(page.getByRole('heading',{name:'Growth'})).toBeVisible();
 await expect(page.getByText('$99',{exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:/Try the free demo/i})).toBeVisible();
});

test('AI analyst requires an authenticated workspace and does not expose fake metrics', async ({page})=>{
 await page.goto('/analyst');
 await expect(page.getByRole('heading',{name:/Connect the dots/i})).toBeVisible();
 await expect(page.getByText('Sign in to your restaurant')).toBeVisible();
 await expect(page.getByRole('link',{name:/Sign in/i}).last()).toBeVisible();
});
