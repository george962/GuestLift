# v0.6 — Website, accounts and operations

## Routes and ownership

| Audience | Route | Purpose | Backend dependence |
|---|---|---|---|
| Visitor | `/` | Problem/benefit, animated tour | None (synthetic sample) |
| Visitor | `/product` | Step-by-step explanation | None |
| Visitor | `/pricing` | Transparent proposed plans | None |
| Visitor | `/start` | Choose demo or account | None |
| Visitor | `/workspace` | Sample analytics and questions | None for public sandbox; backend for account AI |
| Visitor | `/connect` | Guided fictional data import | Browser import only |
| Visitor | `/help` | Self-service FAQ, project issues | None |
| User | `/sign-up`, `/sign-in` | Supabase registration and login | Configured Supabase |
| User | `/forgot-password`, `/reset-password` | Auth email recovery | Configured Supabase + allowlisted redirect |
| User | `/onboarding` | Save account business profile | Verified Supabase token + FastAPI |
| User | `/account` | Access profile and subscription | Supabase to identify account |
| User | `/settings` | Manage business profile | Verified Supabase token + FastAPI |
| User | `/billing` | Plan status, test Checkout and portal | Verified Supabase token + FastAPI + Stripe test config |
| Technical | `/import`, `/demo`, `/campaigns`, `/offers`, `/how-it-works` | Legacy deep links | Browser synthetic tools / localhost demo API |

## How to manage it in practice

- **Pages and marketing copy:** Edit Next.js in `frontend/app`; commit to `george962/GuestLift` and deploy via your hosting provider. The new brand is provisional; the original repository and internal code identifiers have not been renamed.
- **User registration:** Manage authentication, confirmation emails and allowed redirect URLs in your own Supabase project. Use custom email templates, domain and SMTP only after configuring a production support policy.
- **Password reset:** Supabase must allow your actual host's `/reset-password` URL. Account recovery requires an emailed recovery session; the route does not allow arbitrary password changes without an authenticated session.
- **Subscriptions:** Manage products, test prices, customer status, invoices and the test billing portal from Stripe Dashboard in test mode. The app **does not** grant access based on a checkout return alone: webhook-verified status is read from the server.
- **Pricing changes:** Changing the marketing text is **not** sufficient to change what is charged. Update Stripe Price IDs, backend configuration, user-facing terms, and entitlements together. Stripe Prices are generally created as new objects when changing amounts.
- **Customer support:** The current site points to a GitHub issue tracker. Before a commercial launch, establish a real business support address, refund/cancellation handling, incident response, and sensitive-data-safe support workflows.
- **Admin and team management:** A production admin console **does not exist yet**. Avoid pretending it does. A future admin console needs role-based authorization and audit trails. In development, admin provider dashboards are used for Supabase and Stripe.
- **Production hosting:** Static frontend only for the current public demo. Authenticated API should remain local/test-only until tenant security and ingress hardening are complete.

## Branding and media

- Temporary new name: **TableSignal**. No assertion of trademark clearance or domain availability. Validate before ordering assets, acquiring a domain or billing customers.
- Animated tour uses native React, CSS keyframes, a pause control and three sample dashboard states. It works offline and provides a reduced-motion path.
- To add real video later, record a short **original** screencast from the verified app (not borrowed footage), optimize MP4/WebM, provide captions/poster/transcript, honor reduced-motion autoplay preferences, and keep static fallbacks.

## Why not live billing or file uploads now?

The backend is a demo service with unauthenticated non-merchant endpoints. Supabase workspace profile/billing is intentionally isolated from **fictional** seeded data. Merchant SaaS operation requires serious authorization, governance, privacy and commercial-compliance work. Real uploads and live Stripe keys would create a false impression of readiness.

## Acceptance checklist on user's Mac

1. `docker compose up --build -d` finishes without frontend compilation errors.
2. Check `/`, `/start`, `/product`, `/pricing`, `/workspace`, `/help` in browser and on phone viewport.
3. The homepage animation advances, can be paused, and switches when clicking other scenes.
4. The sample workspace has exactly four primary analytical sections and data/account links outside them.
5. `/sign-in` visibly reports unavailable status when Supabase is not configured. After configuration, verify actual signup, email verification, login, logout and reset link.
6. `/billing` cannot produce a test checkout without verified sign-in and Stripe test credentials; when configured, validate webhook and server state.
7. With `GUESTLIFT_STATIC_EXPORT=1`, the public site should **not** call the visitor's localhost backend.
8. Confirm no real merchant/customer records are ever uploaded or sent to an optional AI API.
