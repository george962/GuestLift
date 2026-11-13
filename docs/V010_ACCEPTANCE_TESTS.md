# v0.10 acceptance tests

## Automated checks verified in the release builder

- `PYTHONPATH=backend python -m pytest -q backend/tests`: 45 passing, including new signup/onboarding persistence, draft saving, account isolation, Stripe SDK object handling, scenario validation and 30-day cookie expiry configuration.
- `cd frontend && npm test`: 39 passing JavaScript/source-level tests.
- TypeScript parser via globally available TypeScript compiler: parsed TS/TSX files without syntax diagnostics. **This is not a complete Next.js typecheck or production build.**

## Required on the Mac before release acceptance

1. Run `docker compose up --build -d` and inspect both backend/frontend builds. This is required because the release builder couldn't download npm packages for a full local Next build.
2. Run `docker compose exec -T backend python -m pytest -q` and `docker compose exec -T frontend npm test`.
3. Run `docker compose exec -T frontend npm run lint` (a real TypeScript typecheck).
4. With Docker services running, for actual browser tests run `cd frontend && npm install && npx playwright install chromium && npm run test:e2e`. This is **not verified in the release builder**.
5. Public: open Home, pricing, sample demo and create account. Confirm sign up leads to `/account/welcome`.
6. Private: save restaurant details, choose plan, navigate away, reload, and revisit `/onboarding`; saved step must persist.
7. Billing: existing active Growth status remains verified. Never create another test subscription just to test navigation. Test customer portal only. For *new test accounts*, test Stripe Checkout and `/billing/success` separately.
8. Square: connect a fictional Sandbox seller; sync, verify completion and opportunities CTA; sync again, verify records are idempotent.
9. Opportunities: no-data empty state, observed discounts and customer coverage after sync, scenario arithmetic, save a draft and reopen under Experiments. Verify drafted plans do **not** send messages.
10. Second account: cannot list or update the first account's plans; cannot see the first account's orders.
11. Session: reload dashboard and cross multiple private pages. Temporary backend outage should show a connection issue, not silently erase a logged-in session. Manual signout must work.
12. Mobile keyboard: check private nav, Account dropdown, forms and error messages at mobile width.

## Remaining explicit blockers for real production customers

Use hosted HTTPS and production-worthy auth, CSRF/session policies, email verification/recovery, subscription lifecycle monitoring, data deletion/retention, privacy and merchant API approvals, service monitoring, backup/restore, idempotency and financial reconciliation audits, and real permissions for marketing sends. These are *not* completed in v0.10.
