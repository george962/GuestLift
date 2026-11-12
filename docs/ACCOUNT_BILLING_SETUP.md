# Optional Stripe subscription testing — TableSignal v0.8

## Local account registration works before billing

TableSignal no longer uses Supabase. **First test the complete signup, profile, logout, and sign-in workflow locally**. This requires only the Docker stack, and a fake restaurant profile. `/billing` shows the Sandbox subscription until you configure Stripe test mode.

## Stripe — test mode ONLY

1. Create a Stripe test account at https://dashboard.stripe.com. You do not need a paying customer, business entity, or a verified live payment setup to prototype test mode. Do not invent business or tax information if Stripe requests it; consider using Skip where appropriate.
2. In the Stripe Dashboard, enable **test mode**, create a product and a **recurring monthly Price**, and copy its test Price ID (starts `price_`). The displayed $149/location/month is a proposal; current test Checkout uses quantity **one**, not actual location metering.
3. In your **ignored** `~/GuestLift/.env` (create it from `.env.example` if needed), set:

```dotenv
STRIPE_SECRET_KEY=sk_test_YOUR_TEST_SECRET
STRIPE_GROWTH_PRICE_ID=price_YOUR_TEST_RECURRING_PRICE
GUESTLIFT_APP_URL=http://localhost:3000
```

4. From a separate local Terminal, use the official Stripe CLI to forward signed test webhooks:

```bash
stripe login
stripe listen --forward-to http://localhost:8000/api/saas/billing/webhook
```

5. Copy the listener's signing secret into `.env`:

```dotenv
STRIPE_WEBHOOK_SECRET=whsec_YOUR_TEST_WEBHOOK_SECRET
```

6. Rebuild the backend after changing the environment:

```bash
cd "$HOME/GuestLift" || exit 1
docker compose up --build -d
```

7. Visit http://localhost:8000/api/saas/config and verify test checkout and webhook configuration booleans are true. Sign in to `/billing`, complete a **test** payment using Stripe's published test payment methods, and verify an actual signed subscription webhook updates the displayed plan. A successful redirect alone never grants paid access.
8. Use **Manage test subscription** to open the Stripe test customer portal, if configured; verify changes/cancellations using signed events.

## Important boundaries

- Never use live `sk_live_` credentials in this code. The API rejects live checkout keys.
- The Stripe checkout form is hosted by Stripe. TableSignal stores only subscription/customer identifiers and server-verified status, not card numbers.
- This developer prototype lacks a secure production deployment, complete event-reconciliation policies, tax/legal terms, production invoices, and location quantity billing.
- You can postpone Stripe entirely until product demand is validated.
- Keep secrets in your ignored local `.env` and never paste them in chat or commit them to GitHub.
