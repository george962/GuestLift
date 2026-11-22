/** TableSignal public preview browser regression tests (fictional sample, no live charges). */
import {test,expect} from '@playwright/test';

test('the first screen explains the product and lets visitors open real app paths',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Your sales data has answers/i})).toBeVisible();
  await expect(page.getByText(/Production connections and billing are not enabled/i)).toBeVisible();
  await expect(page.getByText(/fictional business without an account/i)).toBeVisible();
  await expect(page.getByRole('link',{name:/Try the sample workspace/i})).toHaveAttribute('href','/workspace');
  for(const [name,href] of [
    ['Sign in','/sign-in'],['Create account','/sign-up'],
    ['Connect data','/connections'],['AI Analyst','/analyst'],
    ['Billing (test)','/billing']
  ]){
    await expect(page.getByRole('link',{name,exact:true}).first()).toHaveAttribute('href',href);
  }
});

test('hero console is a working sample, not an inert screenshot',async({page})=>{
  await page.goto('/');
  const console=page.locator('.ts12-console');
  await expect(console.getByText('$142,400')).toBeVisible();
  await console.getByRole('tab',{name:/Ask the analyst/i}).click();
  await expect(console.getByText(/Scripted demonstration from fictional data/i)).toBeVisible();
  await console.getByRole('button',{name:/Which guests stopped returning/i}).click();
  await expect(console.getByText(/observed return rate fell/i)).toBeVisible();
  await console.getByRole('tab',{name:/Decision log/i}).click();
  await expect(console.getByText(/Outcome check/i)).toBeVisible();
  await console.getByRole('tab',{name:/Weekly review/i}).click();
  await expect(console.getByText('$142,400')).toBeVisible();
});

test('sample investigation changes evidence without claiming causal lift',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:/Why are fewer identifiable guests returning/i}).click();
  await expect(page.getByRole('heading',{name:/Why are fewer identifiable guests returning/i})).toBeVisible();
  await expect(page.getByText(/Anonymous transactions cannot be assigned/i)).toBeVisible();
  await page.getByRole('button',{name:/What would this use in a real restaurant/i}).click();
  await expect(page.getByText(/permissioned POS order and discount records/i)).toBeVisible();
});

test('location pricing counts verified and selected examples separately',async({page})=>{
  await page.goto('/');
  const pricing=page.locator('#pricing');
  await expect(pricing.getByText('Detected locations')).toBeVisible();
  await expect(pricing.getByText('Eligible in this example')).toBeVisible();
  await expect(pricing.getByText('$297')).toBeVisible();
  await pricing.getByLabel(/Midtown/i).check();
  await expect(pricing.getByText('$396')).toBeVisible();
  await expect(pricing.getByText('Review needed')).toBeVisible();
  await expect(pricing.locator('input[type="checkbox"]:disabled')).toHaveCount(1);
});

test('restored motion tour has accessible controls and a reduced-motion alternative',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/');
  await expect(page.getByLabel('Animated restaurant analytics walkthrough')).toBeVisible();
  await expect(page.getByRole('button',{name:/Pause walkthrough|Play walkthrough/i})).toBeVisible();
  await expect(page.getByRole('button',{name:'Preview Guest behavior'})).toBeVisible();
  await page.getByRole('button',{name:'Preview Guest behavior'}).click();
  await expect(page.getByText(/See who returns and where identities are missing/i)).toBeVisible();
});

test('mobile navigation exposes product and account entry points',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await page.getByRole('button',{name:'Open navigation'}).click();
  const nav=page.getByRole('navigation',{name:'Main navigation'});
  await expect(nav.getByRole('link',{name:'Connect data'})).toBeVisible();
  await expect(nav.getByRole('link',{name:'AI Analyst'})).toBeVisible();
  await expect(nav.getByRole('link',{name:'Billing (test)'})).toBeVisible();
  await nav.getByRole('link',{name:'Product'}).click();
  await expect(page.getByRole('button',{name:'Open navigation'})).toBeVisible();
});
