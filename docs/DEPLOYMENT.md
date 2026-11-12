# GuestLift v0.5 Deployment — Public Demo vs. Private SaaS

## Publish the safe, no-backend sandbox first

This release supports a public-facing static Next.js build. A visitor can try synthetic sales/customer/coupon analysis and the deterministic verified-rules analyst **without an account**. It does not collect personal data or credentials.

A static host such as Cloudflare Pages can deploy `frontend/` from GitHub:

- Repository: `george962/GuestLift`, branch `main`
- Framework: Next.js static HTML export
- Root/build directory: `frontend`
- Build command: `GUESTLIFT_STATIC_EXPORT=1 npm run build`
- Output: `out`
- Do **not** configure public Supabase keys or an API URL for the initial standalone sandbox, unless you have separately designed/secured the entire account flow.

After deploying, check `/`, `/workspace`, `/pricing`, `/how-it-works`, `/import`, `/campaigns`, and mobile navigation. The analyst should show the `verified_rules` engine, not claim access to live restaurant data.

## Authenticated account testing remains local

Use Docker with optional Supabase + Stripe TEST keys as described in `ACCOUNT_BILLING_SETUP.md`. `localhost:8000` has no production auth around the **legacy** v0.1–v0.4 demo endpoints. It **must not** be hosted as a public API. Stripe CLI can forward signed webhooks to localhost while testing.

Before hosting a private restaurant service, create an isolated production-only API surface, add tenant-level permission checks to **every** data-access endpoint, use secure storage/retention and formal migration tooling, harden CORS/CSRF, validate integration scopes, enforce AI quotas and get an independent security review. Use Stripe live billing only after those requirements are met and merchant-facing legal documents/support exist.

The first public website is a **product demonstration**, not a payment-collecting SaaS launch.
