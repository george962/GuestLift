# Square Sandbox — connect your first real API test account

**Read this before connecting anything.** All integration endpoints are hardcoded to `https://connect.squareupsandbox.com`. Real Square sellers, production tokens and real guest records are **not supported in v0.9**. Square's Sandbox is a simulated environment. Do not paste access tokens in TableSignal forms or ChatGPT.

## Method A — the first successful test (recommended)

1. Create or sign into a Square Developer account: https://developer.squareup.com/apps
2. In Developer Console, create an application. Use the **Sandbox** environment, not Production. Under Sandbox credentials, copy your own **Sandbox access token** privately. The default Sandbox test account has such a token; it's suitable only for your development and has broad permissions.
3. On your Mac, go to `~/GuestLift` and create `.env` if it does not already exist: `cp -n .env.example .env`. Do not overwrite an existing `.env`.
4. Edit **only on your Mac**: set `SQUARE_SANDBOX_ACCESS_TOKEN=...` inside `.env`. Never commit or share that file. A developer's access token is NOT acceptable to collect from other merchants; those will eventually use OAuth.
5. Restart your backend: `docker compose up -d --force-recreate backend`.
6. Visit `http://localhost:3000/sign-up` and create a local test account. Complete `http://localhost:3000/onboarding`.
7. Visit `http://localhost:3000/connections`, choose **Connect my Sandbox**. It verifies the token and merchant by calling Square's `ListLocations` endpoint.
8. Select **Sync last 180 days**. TableSignal calls `ListPayments` and `SearchOrders`, checks order and customer references and stores tenant-scoped SQL records. Refresh `/dashboard`.
9. If the dashboard has zero orders, the default Sandbox seller may simply have no completed orders in the last 180 days. This is *correct*—we won't substitute fabricated numbers into a private dashboard.

## Make Square API-created orders for a convincing demo

For your **own** Sandbox only, this release includes the optional `backend/app/dev_seed_square.py` script. It creates four fictional customer profiles and eight fictional test orders and attempts simulated payments to complete the orders. It uses **Square's Sandbox**, not TableSignal's packaged CSV fixtures. It requires the developer Sandbox token with `CUSTOMERS_WRITE`, `ORDERS_WRITE`, and `PAYMENTS_WRITE` permissions.

After reviewing the script, run from `~/GuestLift`:

```bash
docker compose exec backend env TABLESIGNAL_SEED_CONFIRM=YES python -m app.dev_seed_square
```

If the Square Sandbox API reports a validation error, the script stops and may leave previously created test objects. Fix the developer/API configuration and inspect the Square Sandbox Dashboard before running it again. The initial v0.9 release cannot assert this script was executed against your Square account. **This is optional**; Square's official [API Explorer](https://developer.squareup.com/explorer) also lets you create test orders, payments and customers in the Sandbox.

After the script succeeds, click **Sync** in TableSignal. Because Square's API can be eventually consistent, you may need to sync again to see just-created payments/orders.

## Method B — simulate the restaurant owner authorizing the app

For a proper developer OAuth exercise, configure a Sandbox **application ID**, **secret**, and callback in the Square Developer Console. The redirect should be exactly the locally configured callback:

`http://localhost:8000/api/integrations/square/oauth/callback`

The Square Developer Console may restrict which redirect URLs it accepts; if local HTTP callbacks aren't supported in your configured environment, use an appropriately secured developer tunnel and update the env + allowlist only after a security review. Do **not** publish the current backend to a public URL merely to make OAuth work.

Add these to ignored local `.env`:

```dotenv
SQUARE_SANDBOX_APP_ID=YOUR_SANDBOX_APP_ID
SQUARE_SANDBOX_APP_SECRET=YOUR_PRIVATE_SANDBOX_APP_SECRET
SQUARE_SANDBOX_REDIRECT_URI=http://localhost:8000/api/integrations/square/oauth/callback
TABLESIGNAL_CREDENTIAL_KEY=YOUR_FERNET_KEY
```

Generate a Fernet key with the backend (this output is sensitive; do not send it to anyone):

```bash
docker compose exec -T backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

After changing `.env`, recreate the backend. In `/connections`, select **Authorize with Square Sandbox**. The backend creates a random 10-minute OAuth state linked to your account; it exchanges the returned code server-side and encrypts the resulting credentials. It requests only `ORDERS_READ`, `PAYMENTS_READ` and `MERCHANT_PROFILE_READ` in Sandbox. **No OAuth access or refresh token is returned to the browser.** A seller can later revoke app authorization; this local release supports deleting local credentials, but OAuth revocation webhook processing remains future work.

## Data contract and restrictions

- Supported: Square Sandbox completed USD orders for the most recent 180 days, merchant locations, payment-to-order customer ID linkage (if available), discounts, timestamps and repeat detection where customer identifiers are stable.
- Not complete: taxes/tips/service charges accounting, returns, refund matching, partial payments, currencies other than USD, long historical backfills, loyalty campaign attribution, dynamic merchant OAuth production, streaming sync, payroll/inventory data, real PII security controls.
- SearchOrders uses sorted, paginated API results. Each location batch is capped at 800 records; exceeding it fails the sync rather than silently reporting a partial dataset. Use a shorter window and adapt the importer before handling larger datasets.
- Every sync writes a `square_sandbox_sync_runs` status record and rolls back order writes if an API request fails.
- A Sandbox seller can only be linked to one local TableSignal workspace at a time; connecting the same seller from another test account returns 409.
- Delete all local imported orders and connection credentials using **Disconnect**; if you used OAuth, also revoke the application's authorization in the Square Sandbox seller account.

## Why the company would eventually charge for this

The future paid value proposition is one-time managed onboarding, scheduled synchronization, trustworthy private dashboards and AI analytics—not recurring manual CSV uploads. Today's **assisted setup request** is stored in local SQL for developer review and does NOT send a message or guarantee human support.

Useful official references: [Square Sandbox](https://developer.squareup.com/docs/devtools/sandbox/overview), [SearchOrders](https://developer.squareup.com/reference/square/orders-api/searchorders), [ListPayments](https://developer.squareup.com/reference/square/payments/ListPayments), [Sandbox OAuth](https://developer.squareup.com/docs/oauth-api/overview).
