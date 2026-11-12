# v0.7 site owner guide — TableSignal

## The customer journey

1. Visitor lands on animated `/` explaining customers, sales, and campaign intelligence.
2. They can view `/start` → `/workspace` immediately, using a **fictional** demonstration.
3. `/pricing` → Growth plan → `/sign-up?next=%2Fbilling`.
4. With configured Supabase, account is created and confirmation email may be required. `/sign-in` leads to `/billing` after verification.
5. New accounts visit `/onboarding` to save restaurant type, name and objective, then use `/workspace` or `/billing`.
6. `/billing` calls verified FastAPI to create a Stripe **test** Checkout session, which redirects to Stripe-hosted test payment UI. Stripe signs and sends subscription lifecycle events to the webhook endpoint; the backend updates entitlement.
7. Returning operators visit `/account`, `/settings`, `/billing` to manage their profile and plan; Stripe Billing Portal supports test subscription changes when configured.

## What the founder uses to maintain customers today

- Account identities: **Supabase Dashboard → Authentication → Users** (test project).
- Payments/subscriptions: **Stripe Dashboard → Test mode → Customers, Subscriptions, Billing**.
- Synthetic workspace summary: private `GET /api/saas/me` authorized per Supabase user; do not call as another user or expose database directly.
- Health/readiness: `GET /api/health` and `GET /api/saas/config` locally.
- Website updates: existing GitHub repo `george962/GuestLift` and deployment pipeline once separately set up.

The prototype does not have a staff admin UI, email support queue, production logs, real merchant billing, or a secure public API. Do not present it as a commercially ready service.

## Motion design notes

- The new landing integrates five motion categories: timed hero scene rotation, ambient/floating accents, looping ticker, scroll-triggered reveals, and clickable story/analyst demos.
- UI uses native CSS animation and React state, with user control and `prefers-reduced-motion` behavior. No licensed music, misleading stock video, external tracking, or separate animation runtime.
- `frontend/components/landing-experience.tsx` defines the new content and interactivity; `frontend/app/globals.css` contains `v7-*` styles; the preexisting `MotionTour` runs the hero rotation.
- The standalone `PREVIEW.html` is a **design preview only**; actual app routes and authentication must be tested in local Next.js and connected services.

## Before charging customers

Implement hardened hosting, isolate unauthenticated synthetic demo endpoints, secure tenant data and connections, complete multi-tenant account controls, use separate dev/staging/prod infrastructure, define subscription quantity and billing terms, robust webhook recovery, refunds, disputes, taxes, data retention, independent security audit, reviewed legal terms and first operator pilot. Only afterward consider accepting live Stripe keys and merchant data.
