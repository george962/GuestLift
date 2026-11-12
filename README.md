# TableSignal v0.8 — Local accounts and restaurant workspaces

**Know your guests. Grow with clarity.** TableSignal remains a prototype restaurant intelligence platform with an animated product website, a sample sales and customer dashboard, promotion analysis, and a rules-based analyst grounded in synthetic transaction metrics.

## What changed in v0.8

**Supabase was removed.** You do not need an external identity service, hosted database, account credentials, or a company registration to test the local app.

- Create an email/password **developer account** at `/sign-up`; passwords are hashed using Argon2id.
- Sign in at `/sign-in` using a revocable, 7-day, **HttpOnly cookie**; session tokens are hashed in PostgreSQL rather than kept in localStorage.
- Set up a fictional restaurant profile in `/onboarding` and edit it later in `/settings`.
- Each local user receives a separate synthetic restaurant workspace and can revisit it after a Docker restart.
- Sign out on `/account`; change a password on `/reset-password` after supplying the current password. Password changes revoke other sessions.
- Browser-to-API requests use credentialed CORS restricted to local site origins, plus origin checks and anti-forgery tokens for state-changing authenticated endpoints.
- Existing operator dashboard, campaign models, import demo, animated homepage, and **optional Stripe test mode** are preserved.
- No live payments, real merchant data, or production hosting are enabled.

## Start the app locally

The ZIP contains the **complete replacement project** (not a patch). Copy its contents into the existing `~/GuestLift` folder, keeping that folder's `.git` and any private `.env` file. If you've already copied v0.8 into `~/GuestLift`, skip copying and **do not unzip or reinstall again**.

From the project root:

```bash
cd "$HOME/GuestLift" || exit 1
grep '"version"' frontend/package.json
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose ps
```

The frontend should report `0.8.0` and the services should be available at:

- Homepage: http://localhost:3000
- Sign up: http://localhost:3000/sign-up
- Sign in: http://localhost:3000/sign-in
- Saved restaurant profile: http://localhost:3000/settings
- Account and password change: http://localhost:3000/account
- Test billing: http://localhost:3000/billing
- Backend API docs: http://localhost:8000/docs (development only)

**No Supabase, Stripe, or OpenAI keys are required to register and use local sample accounts.** Stripe test Checkout remains disabled until its own **test-only** keys are configured.

## End-to-end local account walkthrough

1. Open `/sign-up`, enter a developer email and a password with at least 12 characters.
2. Registration creates a local user record and session automatically; complete `/onboarding` with a fictional restaurant name and goal.
3. Visit `/settings`, save a change, then `/account` and sign out.
4. Sign in again with the same email/password. Your restaurant profile and synthetic workspace should persist.
5. Create a second test account. Its restaurant profile remains separate. Each account starts with the same **fictional** seed dataset, not shared writable records.
6. Optionally open `/billing` to see the Sandbox tier. Stripe test checkout requires separate configuration; no real charges are enabled.
7. To change your password, sign in and visit `/reset-password`. Email reset is intentionally unavailable without a mail delivery service. A local developer recovery CLI is documented below.

## Where data is stored

| Record | Local storage |
|---|---|
| User email + Argon2id password hash | `local_users` table in the existing PostgreSQL Docker volume |
| Hashed session token + expiry + CSRF secret | `local_sessions` table in the same database |
| Restaurant name, goals, synthetic orders | `saas_workspaces`, `saas_workspace_demo_orders` |
| Optional test subscription status + Stripe references | `saas_workspaces` and `saas_billing_events` |
| Full payment card details | Never stored by TableSignal; Stripe test Checkout handles payment methods |

The local Docker database uses the existing `guestlift_pg` persistent volume. Ordinary rebuilds and `docker compose down` **do not delete** that volume. `docker compose down -v` **does delete** the database, including accounts. Do not run that command unless you intend to lose the data. Back up before migrating your development database.

## Account and billing limitations

These accounts are suitable for local developer testing only. There is no confirmed-email signup, automatic email recovery, user invitation/team role system, production rate limiting, security monitoring, hosted backups, or completed tenant security audit. The existing legacy fixture API also includes unauthenticated routes; **never expose port 8000 to the public internet**.

The demonstration contains fictional Toast/Square-shaped order records. It does not establish real marketing incrementality or profit lift. The AI analyst is read-only and model-based explanations are disabled unless explicitly configured on the backend for fictional aggregate data.

## Documentation

- [Local account setup, testing and recovery](docs/LOCAL_ACCOUNT_SETUP.md)
- [Stripe test billing (optional)](docs/ACCOUNT_BILLING_SETUP.md)
- [Security and storage architecture](docs/SAAS_ARCHITECTURE.md)
- [Roadmap and production blockers](ROADMAP.md)
- [Upgrade guide](UPGRADE_GUIDE.md)

The repository remains `george962/GuestLift`; TableSignal is a working product name, not a verified domain or trademark. This ZIP does **not** automatically commit or deploy the code.
