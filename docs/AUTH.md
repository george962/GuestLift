# Authentication: moving from local accounts to a managed provider

## Status

| Piece | State |
| --- | --- |
| Backend verifies provider-issued bearer tokens (`GUESTLIFT_AUTH_MODE=oidc`) | **Done and tested** (`backend/app/oidc_auth.py`) |
| Backend refuses to start in production with local accounts | **Done** |
| Frontend sign-in, sign-up and token handling | **Not done.** Needs a provider account and keys |
| Provider account, email templates, MFA policy, data-processing agreement | **Yours to do** |

The built-in accounts (`local_auth.py`) are for development. They have no email
verification, no password recovery and an in-memory rate limiter that does not
work across multiple server processes. A managed provider replaces all of that,
so none of it should be built by hand.

## Recommendation: Clerk, unless one of the "choose differently" cases applies

Why it fits this codebase:

- **Next.js frontend.** Prebuilt sign-in, sign-up, password reset and account
  components remove the most work. The existing UI (`auth-panel.tsx`) is already
  shaped like a hosted-auth client.
- **FastAPI backend that only needs to verify a token.** Clerk session tokens are
  standard JWTs with a published JWKS, so the backend needs no Clerk SDK and no
  per-request call to Clerk.
- **One person owns one restaurant workspace today.** `saas_workspaces.owner_sub`
  maps directly to the token's `sub`. Clerk Organizations exist if you later need
  multi-user restaurants, but nothing here requires them yet.

Choose differently if:

- **You need enterprise SSO (SAML) from day one:** look at WorkOS.
- **You move the database to Supabase anyway:** Supabase Auth avoids a second vendor.
- **You need to self-host or keep identity data in your own infrastructure:**
  Keycloak, or Auth0 with a data-residency plan.

Because the backend verifies standard OIDC tokens, switching later means changing
three environment variables and the frontend sign-in components, not the API.

Things to check before committing (these change, so confirm them yourself):
current pricing at your expected user count, where user data is stored, the
provider's data-processing agreement (you will hold restaurant owners' emails),
and how to export users if you ever leave.

## Backend settings

```
GUESTLIFT_ENV=production
GUESTLIFT_AUTH_MODE=oidc
GUESTLIFT_OIDC_ISSUER=<exact `iss` in tokens>          # Clerk: your Frontend API URL
GUESTLIFT_OIDC_JWKS_URL=<issuer>/.well-known/jwks.json  # must be https in production
GUESTLIFT_OIDC_AUTHORIZED_PARTIES=https://app.example.com   # Clerk: checked against `azp`
# GUESTLIFT_OIDC_AUDIENCE=   # only if your provider puts `aud` in tokens
```

The app refuses to start if these are missing or inconsistent, rather than
silently falling back to local accounts.

What the backend enforces on every request: signature (asymmetric algorithms
only; `none` and HMAC are rejected), `exp`, `nbf` when present, `iss`, `sub`, `aud`
when configured and `azp` when configured. Signing keys are fetched from the JWKS
by `kid`, cached for five minutes, and refetched on an unknown `kid` at most once
every 10 seconds. After a key rotation, tokens signed by the new key can be refused
for up to that long; providers publish new keys ahead of use, so this is normally
invisible. If the provider's key endpoint is unreachable the API returns **503**,
not 401, so an outage is not mistaken for a bad login.

Users are stored as `oidc:<sub>` in `saas_workspaces.owner_sub`, so they cannot
collide with local development accounts.

Once `oidc` mode is on, `/api/local-auth/*` returns 404 and cookie sessions are
ignored, so there is no second way in.

## Frontend work still to do

All pages call the API through `accountApi()` in `frontend/lib/local-auth.ts`, and
the auth surface used by the UI is `localAuthClient()`. That is the seam.

1. Install the provider SDK and add its publishable key to the frontend environment.
2. Replace `components/auth-panel.tsx` with the provider's sign-in and sign-up components.
3. Re-implement `localAuthClient()` (`getSession`, `signOut`, `onAuthStateChange`)
   on the provider's client so existing pages keep working.
4. Change `accountApi()` to send `Authorization: Bearer <fresh token>`. Remove the
   cookie, `credentials: 'include'` and the `X-CSRF-Token` logic: bearer tokens are
   not sent automatically by browsers, so CSRF does not apply. Fetch a new token
   for each call. Clerk session tokens last about a minute, so never store one.
5. Delete the password-change and recovery stubs; the provider handles them.
6. Set the provider to require a verified email before it issues a session. The
   backend trusts the provider on this and does not re-check it.
7. If you turn on Clerk Organizations with required membership, tokens for users
   without an organization carry `sts: pending`; decide whether to reject them.
8. Cross-origin: the API must list your frontend in `GUESTLIFT_ALLOWED_ORIGINS`.
   Same-origin cookie-based verification is not implemented; use the header.

## Rollout order

1. Create the provider project; keep development and production instances separate.
2. Set the backend variables on a staging deployment and verify `GET /api/saas/me`
   with a real token.
3. Ship the frontend change behind the same staging environment.
4. Existing local accounts hold no real merchant data (the app is development-only
   and the demo is synthetic), so there is nothing to migrate. If that stops being
   true, write a one-off script mapping `local_users.id` to the new `oidc:<sub>`.
5. Only then set `GUESTLIFT_ENV=production` on the live deployment.

## Frontend in Clerk mode (M2)

Build the frontend with `NEXT_PUBLIC_AUTH_MODE=clerk` and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, and run the backend with `GUESTLIFT_AUTH_MODE=oidc` plus the issuer/JWKS settings above. Sign-up, email verification, password reset and the security page are Clerk's own screens (`/sign-up`, `/sign-in`, `/reset-password`). Every API call sends a fresh Clerk session token as `Authorization: Bearer`; a 401 shows a "session ended" banner.

Clerk dashboard settings:
- **Email + password** sign-in, with **email verification required**.
- **Organizations: off**, or at least "membership optional". TableSignal manages teams itself (owner and manager roles in `app/membership.py`); with organizations required, Clerk adds an extra "Set up your organization" screen after sign-up.
- **Allow users to delete their account: on**. "Delete workspace and account" in Settings deletes the Clerk user after the workspace.

Teams: owners invite managers from Settings. The invite link works once and expires after 7 days. Managers can view, sync and save decisions; only owners can connect Square, manage billing, invite or remove people, or delete the workspace.

Testing: `JOURNEY_AUTH_MODE=clerk scripts/journey.sh` runs the full journey against the development instance using `+clerk_test` emails, which accept the code 424242 and send no mail. CI runs it in the `journey-clerk` job when the `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` and `GUESTLIFT_OIDC_ISSUER` repository secrets exist.
