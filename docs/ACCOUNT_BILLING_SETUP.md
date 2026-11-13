# TableSignal v0.9 — local accounts and optional Stripe TEST billing

**Supabase is NOT used.** TableSignal runs developer-only accounts in the existing local PostgreSQL Docker database. This replaces all v0.7 cloud-Supabase setup instructions.

## Local accounts (no external provider)

1. From `~/GuestLift`, run `docker compose up --build -d`.
2. Visit http://localhost:3000/sign-up and register a **test** email/password. Passwords require 12+ characters and are stored as Argon2id hashes. A random HttpOnly session cookie persists login.
3. At `/onboarding`, save your restaurant profile, choose Free development Sandbox or view Growth test checkout, and connect Square Sandbox at `/connections` when ready.
4. The private `/dashboard` starts empty. It does NOT copy fictional sample numbers into the user's business. The public `/workspace` is a clearly separate sample demo.
5. `/settings` edits the saved profile. `/account` allows sign out and `/reset-password` allows changing a password while signed in. Email/password reset links are not enabled for these local test accounts.
6. For an intentionally local developer reset of a locked-out test account, see `docs/LOCAL_ACCOUNT_SETUP.md`. Never delete your database to reset a password.

To inspect local test customers and assisted-setup requests (no secrets shown):

```bash
docker compose exec -T backend python -m app.dev_admin
```

## Stripe test mode (optional; DO NOT use live keys)

1. Create a Stripe account and a recurring **test-mode** Price in https://dashboard.stripe.com/. The website's $149/location/month is an unvalidated proposal; the actual test checkout amount comes from your Stripe Price. Quantity is fixed at one—not real per-location billing.
2. In your local, ignored `~/GuestLift/.env`, enter `STRIPE_SECRET_KEY=sk_test_...` and `STRIPE_GROWTH_PRICE_ID=price_...`. Never commit the file.
3. On your Mac, install Stripe CLI and run `stripe listen --forward-to http://localhost:8000/api/saas/billing/webhook`. Add the CLI's `whsec_...` test signing secret to `.env` as `STRIPE_WEBHOOK_SECRET`.
4. Recreate backend: `docker compose up -d --force-recreate backend`.
5. Open http://localhost:8000/api/saas/config. Both `test_checkout_configured` and `test_webhook_configured` should be `true`; no keys are returned.
6. Register/sign in, save restaurant profile, open `/billing`, start Stripe **test** checkout, use Stripe-published test payment methods, then return and refresh subscription status. Browser redirect alone NEVER grants Growth access; a verified signed `customer.subscription` webhook does.
7. Test cancellation through Stripe's test Customer Portal and check that private AI access is revoked. Checkout does not automatically import POS records, which requires the separate `/connections` workflow.

The public sample analyst is not paid. Account-based AI is gated by verified subscription status and also requires a connected data source. You can test free Square Sandbox imports without a subscription **only in the local developer mode**.

## Where information goes

| Data | Where |
|---|---|
| Developer email / salted password hash | Local PostgreSQL `local_users` |
| Revocable session secret hash and anti-forgery token | Local PostgreSQL `local_sessions` |
| Restaurant profile / test subscription state | Local PostgreSQL `saas_workspaces` |
| Connected Sandbox orders and OAuth token ciphertext | Local PostgreSQL `square_sandbox_*` |
| Developer Square Sandbox access token | Local ignored `.env` backend only |
| Card information, test invoices, test subscriptions | Stripe's external test environment (not local database) |
| Stripe customer/subscription IDs + signed webhook event IDs | Local PostgreSQL |

## What is not ready

- Production credit-card billing, domain or server hosting, email verification/recovery, production vendor OAuth, payment failure/retry policies, team roles, secure merchant data upload, real financial reconciliation and a founder web admin console.
- The old unauthenticated demo fixture API has a reset route and must remain bound to 127.0.0.1. **Do not publish the backend publicly.**

See `docs/PRODUCTION_READINESS.md` for launch blockers. Real seller/customer data and live payments are forbidden in this prototype.
