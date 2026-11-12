# Set up TableSignal account creation and subscription testing (v0.7)

This guide describes an **actual working external authentication + billing integration once credentials are configured**. It is currently restricted to **test accounts, test payments and fictional restaurant data**. The UI pages exist in the source without those credentials, but cannot magically create Supabase users or Stripe payment sessions until you connect your own external services.

**Important:** Do not paste secret credentials into ChatGPT, GitHub, screenshots or the public frontend. Add them only to a local ignored `.env` or a secure hosted secret manager.

## 1 — Set up Supabase for accounts

1. At <https://supabase.com/dashboard>, create a test development project.
2. Under Authentication, enable the Email/password provider. Enable email confirmation; configure SMTP before sending production account emails. Supabase's development mail service has limits.
3. Under Authentication → URL Configuration, set **Site URL** `http://localhost:3000`. Add these **allowed Redirect URLs**:
   - `http://localhost:3000/sign-in`
   - `http://localhost:3000/sign-in?next=*`
   - `http://localhost:3000/reset-password`
   - `http://localhost:3000/onboarding`
4. In Supabase project settings copy the **Project URL** and **publishable/anon API key**. Use the same public URL/key in frontend and backend. **Never use a Supabase secret/service-role key here.**
5. In the `~/GuestLift` root (your existing Mac folder) create `.env` from the provided `.env.example` if you do not already have one. Add:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_KEY
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_KEY
GUESTLIFT_APP_URL=http://localhost:3000
```

6. Run `docker compose up --build -d` again so the **frontend rebuild** receives the `NEXT_PUBLIC_` variables.
7. Open http://localhost:3000/sign-up and create your *own test* account. Check confirmation email, then sign in at http://localhost:3000/sign-in. The app verifies tokens against Supabase on the backend and stores a separate **synthetic seeded** restaurant workspace per account.
8. Open `/account` to manage profile, `/settings` to edit restaurant goal/name and `/billing` to see plan status. Test reset flow at `/forgot-password` → `/reset-password`.

> Supabase redirect allow-list details: <https://supabase.com/docs/guides/auth/redirect-urls> and password login: <https://supabase.com/docs/guides/auth/passwords>.

## 2 — Set up Stripe test subscriptions

1. Create a Stripe **test** account at <https://dashboard.stripe.com/> and enable **Test mode**. Create a Product, e.g. `TableSignal Growth (test)`, and a **recurring monthly Price**. The site's $149 per location is a **proposed price**; your actual Stripe Price controls the test checkout amount. This code uses a fixed quantity of one: location-based metering is **not implemented**.
2. Get a Stripe **test secret key** (starts `sk_test_`) and **test Price ID** (starts `price_`). Put them in ignored `~/GuestLift/.env`:

```dotenv
STRIPE_SECRET_KEY=sk_test_YOUR_TEST_KEY
STRIPE_GROWTH_PRICE_ID=price_YOUR_TEST_RECURRING_PRICE
```

3. Install the official Stripe CLI (<https://docs.stripe.com/stripe-cli>) and authenticate with `stripe login`.
4. In a **second Terminal window** start the webhook listener with this exact local path:

```bash
stripe listen --forward-to http://localhost:8000/api/saas/billing/webhook
```

5. Copy the listener's `whsec_...` signing secret into your existing root `.env`:

```dotenv
STRIPE_WEBHOOK_SECRET=whsec_YOUR_TEST_LISTENER_SECRET
```

6. Recreate backend: `docker compose up --build -d`.
7. Open http://localhost:8000/api/saas/config and check that `auth_configured`, `test_checkout_configured` and `test_webhook_configured` all read `true`. **No credentials will be shown in this endpoint.**
8. Use this complete path in your local website:

   **Pricing → Growth → Create account → Confirm email → Sign in → Save restaurant profile → Billing → Continue to Stripe test checkout.**

9. Stripe hosts the payment form; use its published test card examples, not a live card. Return to `/billing`, then click **Refresh plan status** after the `customer.subscription.created/updated` event arrives. A checkout success URL **never** grants entitlement by itself.
10. Test cancellation/change through **Manage test subscription** after enabling the Stripe Customer Portal in test mode. Check that an inactive subscription removes the `Growth` entitlement.

### Why the billing button may be disabled

- **Sign in isn't configured:** missing Supabase project URL or public key on frontend/backend.
- **Account is unsigned:** sign in at `/sign-in?next=%2Fbilling`.
- **Stripe isn't configured:** missing `sk_test_...` key or `price_...` recurring Price ID in `.env`; rebuild backend.
- **Webhooks not active:** Stripe may show completed test checkout, but access waits for a verified subscription status event.
- **Billing portal isn't configured:** turn on customer portal in Stripe test dashboard and have a Stripe customer created through test checkout first.
- **Public static deployment:** the browser's `localhost:8000` backend is *the visitor's computer*, not your server. Account-based billing requires a proper, secured hosted API. **Do not deploy the current unauthenticated legacy fixture endpoints**.

## 3 — What is a real subscription vs this prototype?

| Workflow | v0.7 status |
|---|---|
| Public animated product page | Implemented, synthetic-only |
| Free fictional analytics demo | Implemented |
| Supabase email sign-up, sign-in, recovery | Implemented in frontend; requires your external configuration |
| Per-account synthetic restaurant profile | Implemented; requires Supabase + backend |
| Stripe recurring test Checkout | Implemented; requires Stripe test keys and Price |
| Stripe subscription event verification | Implemented in local backend; requires signed test webhook |
| Stripe test customer portal | Implemented foundation; requires portal/test customer |
| Production cards, invoices, taxes, refunds and location quantities | **Not implemented** |
| Secure public merchant backend and real POS integrations | **Not implemented** |
| Live payments or access to real guest/customer records | **Disabled** |

## 4 — Before the first real paying customer

**Do not switch to live Stripe keys in v0.7.** First implement: protected production API distinct from open demo endpoints, tenant authorization and roles, merchant consent, audit trail, rate limits, secrets management, live transaction reconciliation, webhook ordering recovery, invoice failure policies, Stripe price/quantity validation, tax/legal policies, backup/deletion processes and independent security review. Only then decide on live charges and merchant data ingestion.

For managing customers in the meantime, use **Supabase Dashboard → Authentication → Users** for test identities and **Stripe Dashboard → Test mode → Customers / Subscriptions** for test checkout results. This version does not include a founder/admin console and should not pretend to have one.
