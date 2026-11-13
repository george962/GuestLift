/** Browser-level smoke checks against local Docker. Never talks to production Stripe/Square. */
import {test,expect} from '@playwright/test';

test('public demo is clearly separate from a private account',async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('link',{name:/Try the demo/i}).first()).toBeVisible();
 await page.goto('/dashboard');
 await expect(page.getByText('Sign in to your private workspace')).toBeVisible();
});

test('signup -> welcome -> restaurant -> persisted plan -> signed-in return',async({page})=>{
 const unique=`v10-${Date.now()}-${Math.floor(Math.random()*100000)}@example.test`;
 await page.goto('/sign-up');
 await page.getByLabel('Email address').fill(unique);
 await page.getByLabel('Password',{exact:true}).fill('LocalDeveloper#Test2026');
 await page.getByLabel('Confirm password').fill('LocalDeveloper#Test2026');
 await page.getByRole('button',{name:/Create account/i}).click();
 await expect(page).toHaveURL(/\/account\/welcome/);
 await expect(page.getByText('Your TableSignal account is ready.')).toBeVisible();
 await page.getByRole('link',{name:/Set up my restaurant/i}).click();
 await expect(page).toHaveURL(/\/onboarding/);
 await page.getByLabel('Restaurant name').fill('Harbor Cafe Browser Test');
 await page.getByRole('button',{name:/Save and continue/i}).click();
 await expect(page.getByText('How would you like to start?')).toBeVisible();
 await page.getByRole('button',{name:/Continue free/i}).click();
 await expect(page.getByText('Next: connect your orders.')).toBeVisible();
 // The important check: navigation and reload must not reset the onboarding wizard.
 await page.goto('/dashboard');
 await expect(page.getByRole('heading',{name:'Harbor Cafe Browser Test'})).toBeVisible();
 await page.reload();
 await expect(page.getByRole('heading',{name:'Harbor Cafe Browser Test'})).toBeVisible();
 await page.goto('/onboarding');
 await expect(page.getByText('Next: connect your orders.')).toBeVisible();
 await page.goto('/experiments');
 await expect(page.getByText('No decisions saved yet')).toBeVisible();
 await expect(page.getByRole('link',{name:'Opportunities'}).first()).toBeVisible();
});
