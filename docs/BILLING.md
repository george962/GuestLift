# Billing and entitlements (M5)

All access decisions come from `app/billing.py::entitlement(workspace)`. The UI shows its `message`; no page decides access on its own.

| State | When | Access |
|---|---|---|
| `setup` | Signed up, no complete sync yet | Connect, select locations, sync, view |
| `trial` | First complete sync started a `GUESTLIFT_TRIAL_DAYS` (14) no-card trial | Full |
| `trial_expired` | Trial over, no subscription | Read-only |
| `active` | Paid subscription | Full |
| `canceling` | Canceled at period end | Full until the period ends |
| `past_due` | Payment failed, within `GUESTLIFT_PAYMENT_GRACE_DAYS` (7) | Full, with a "fix billing" banner |
| `read_only` | Grace over, unpaid or canceled | Read-only: numbers stay visible; no syncing, AI analyst or new decisions |

**Paid routes** depend on `paid_subject` (AI analyst, AI questions, creating or updating decisions). **Sync** depends on `sync_subject` (allowed in `setup`, so the trial can start). `tests/test_billing_m5.py` lists both sets: a new paid route must be added there, and every state is tested against every paid route.

The worker doesn't schedule syncs for read-only workspaces.

**Stripe.** Checkout quantity = monitored locations, verified on the server. After paying, Stripe returns to `/billing?checkout=return&session_id=…`, where the page verifies that exact session with Stripe. Webhooks keep state current:
- `customer.subscription.*`: status, period end, cancel-at-period-end
- `invoice.payment_failed`: starts the grace period
- `invoice.paid`: clears it

Each event is verified by re-reading the subscription from Stripe.

**Changing locations while subscribed.** Billing → Change locations → **Preview the price** calls `POST /api/saas/billing/locations/preview` (Stripe's proration preview). **Confirm change** calls `/confirm`, which sets the Stripe quantity and the monitored set together, or changes neither. A newly added location's history is imported automatically.

**LIVE mode** stays off. The code rejects live keys and `livemode` events. Turning it on is a go-live step (`docs/PILOT_TRUST_PLAN.md`).

**Verifying against Stripe.** Run `RUN_STRIPE_TESTS=1 python -m pytest tests/test_stripe_test_clock.py` with TEST keys. A Stripe test clock moves the subscription through these steps:
- active
- a location removal with a prorated credit
- cancel at period end
- two months on a failing card, which goes past due
- canceled, which goes read-only

The clock is deleted at the end.

**Manual check (once).** Stripe's hosted Checkout page uses bot protection, so it isn't automated:
1. Sign up locally, connect, sync, and go to Billing.
2. Choose **Start Growth test checkout** and pay with card 4242 4242 4242 4242, any future date and any CVC.
3. You should land back on Billing with **Your plan: Active**.
