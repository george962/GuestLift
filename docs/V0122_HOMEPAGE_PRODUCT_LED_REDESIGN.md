# TableSignal v0.12.2 — product-led homepage redesign

## Purpose

Make the product immediately understandable: connect restaurant orders, guests,
and discounts; investigate changes with evidence; document an approved next step;
then check the result. More visible software, less generic marketing copy.

## The updated first screen

- Deep ink/navy hero, high-contrast lime accent and warm off-white sections.
- A **working interactive sample console** on the right, with three selectable
  tabs: **Weekly review**, **Ask the analyst**, and **Decision log**.
- The tabs contain invented illustrative data and make that limitation explicit.
  The public ask example is scripted and is NOT a live LLM response.
- Direct demo and account entry links, with no need to scroll to discover what
  this product does.
- Clear three-part value explanation immediately after the hero: **Connect data**,
  **AI Analyst**, and **Decision tracker**.

## Motion

- Hero entry animations, tab transitions, animated sample chart bars, connection
  signal movement, hover affordances, and section entrance cues.
- Restores and retains the original `MotionTour` with automatic playback, manual
  view selection, pause/play, and reduced-motion handling.
- Honors `prefers-reduced-motion: reduce` and keeps the core site usable without
  animation. No critical content depends on a reveal animation to be visible.

## What this changes

Only five frontend paths:

- `frontend/components/v012-experience.tsx`
- `frontend/app/v012.css`
- `frontend/e2e/v012-public.spec.ts`
- `frontend/e2e/customer-journey.spec.ts` (updates the obsolete homepage CTA assertion)
- `frontend/app/page.tsx` (homepage metadata)

The package also includes this document. It does not touch backend, database,
account/auth services, Square credential storage, Stripe keys, or the existing
app routes.

## Safe installation (existing `~/GuestLift` project)

Do **not** replace the project root, do not delete `frontend 2/`, and do not
remove `.env`, volumes or Docker images.

1. Back up the three frontend paths above.
2. Extract the ZIP **into the root of `~/GuestLift`**. The archive has no extra
   enclosing version folder.
3. Run `docker compose build frontend` and `docker compose up -d frontend`.
4. Check `docker compose exec -T frontend npm test` and
   `docker compose exec -T frontend npm run lint`.
5. Run `docker compose exec -T frontend npm run test:e2e` **only if Playwright
   Chromium is installed** and the local backend is running. Browser tests may
   require additional setup.

## What is and is not live

- Public preview: fictional restaurant and scripted example answers.
- Account: existing local authentication and saved workspace.
- Connections: existing Square Sandbox developer path, not production merchant
  integration.
- AI analyst: existing account-scoped functionality, optional model support
  subject to configured backend; public console is illustrative.
- Billing: existing Stripe test checkout. Proposed $99/location price and
  location selector are illustrative; the sandbox test price may differ.

**No production POS OAuth, real merchant data ingestion, campaign execution or
live payments are enabled by this redesign.**

## Test gates

- Frontend Next.js production build / TypeScript compilation.
- Existing 40 frontend unit tests (run in user's Docker).
- Updated Playwright browser tests in `frontend/e2e/v012-public.spec.ts`.
- Visual check of desktop and mobile hero, keyboard tab focus, reduced motion,
  and all real route links.

This package was statically syntax-checked in the build environment, but the
complete Next.js app and runtime flows must be tested in the existing project.
