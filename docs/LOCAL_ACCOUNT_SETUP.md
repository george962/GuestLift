# TableSignal v0.9 — Local account operations

## What to install

Only Docker Desktop and the v0.8 project files are necessary. **Supabase is not used.** The Docker Compose stack runs Next.js (port 3000), FastAPI (port 8000) and PostgreSQL (private container network). The application services are bound to `127.0.0.1` on your Mac.

From the repository root, use:

```bash
cd "$HOME/GuestLift" || exit 1
docker compose up --build -d
docker compose ps
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
```

Try registration at http://localhost:3000/sign-up with **fictional/development** contact details. The private `/dashboard` starts with no orders; connecting Square Sandbox at `/connections` is a separate deliberate action. You'll immediately be signed in, since this local release does not send account verification emails.

## What gets stored

PostgreSQL tables: `local_users` (email + Argon2id password hash), `local_sessions` (SHA-256 hash of random cookie secret, CSRF token, expiry), `saas_workspaces` and `saas_workspace_demo_orders` (restaurant profile and synthetic records). Local session cookies have HttpOnly, SameSite=Strict, a seven-day lifetime, and no readable password/session token in JavaScript. Requests changing private data must include an anti-forgery header plus a local browser Origin. Cookies are deliberately **not Secure** over localhost HTTP; do not use this configuration with any remotely accessible server.

`/api/local-auth/session` returns the current developer account and a CSRF token so the frontend can send authenticated write requests. Account-specific backend routes derive workspace ownership from the server-side session, not a workspace ID provided by the browser.

## Test the full journey

1. Create account A at `/sign-up` and complete the restaurant profile.
2. Visit `/settings`, change the name, save, and reload. It should persist.
3. Register account B in a separate browser profile. Its saved profile must be independent from account A, and its private dashboard should show no orders unless it has its own Sandbox connection.
4. Sign out at `/account` and sign back in at `/sign-in`. Try `/reset-password` while authenticated to change the password after entering the current one.
5. Restart Docker with `docker compose restart`. The database and active session should persist.
6. Optionally configure Stripe **test-only** keys for `/billing`, but no Stripe account is needed for local login.

## Forgotten password in developer mode

There is intentionally no email-delivered recovery link. To reset a local test account when you can't sign in, use an interactive shell **only on your own Mac**:

```bash
cd "$HOME/GuestLift" || exit 1
docker compose exec backend env GUESTLIFT_ALLOW_LOCAL_PASSWORD_RESET=1 python -m app.dev_reset_password
```

Enter the test account email, then type the new password twice at hidden prompts. This revokes all current sessions. The feature is a local operator CLI with no HTTP endpoint; never enable it on a remotely accessible host.

## Optional: Back up the local database

From your Mac Terminal, create a local SQL backup file:

```bash
cd "$HOME/GuestLift" || exit 1
docker compose exec -T database pg_dump -U guestlift guestlift > tablesignal-local-backup.sql
```

Backups contain emails and password hashes, so treat them as sensitive: keep them private, encrypted where possible, and outside GitHub. Do not use `docker compose down -v` unless you want to permanently remove the local volume.

## Limitations

The current app is **not** production-ready. No email verification, external password recovery, TLS, hosted DDoS protection, team permissions, real customer data security controls, or mature session lifecycle management. In-memory login throttling only protects this single local process. The legacy sample-data API is intentionally unauthenticated; port 8000 must never be internet-facing. Signup does not involve a Stripe charge.
