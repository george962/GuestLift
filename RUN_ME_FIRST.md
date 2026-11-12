# Run TableSignal v0.8 locally

1. Download and extract the v0.8 project; **copy its contents** into your existing `~/GuestLift` folder while preserving `.git` and any existing `.env`.
2. If you've already placed the v0.8 files there, **do not unzip or copy anything**. Open Terminal and run the entire block below:

```bash
cd "$HOME/GuestLift" || exit 1

echo "Version:"
grep '"version"' frontend/package.json

echo "Build and start:"
docker compose up --build -d

echo "Backend tests:"
docker compose exec -T backend python -m pytest -q

echo "Frontend tests:"
docker compose exec -T frontend npm test

echo "Services:"
docker compose ps

echo "Git status:"
git status --short
```

3. Open http://localhost:3000/sign-up. Create a development account with a password of 12+ characters. This uses **your existing local PostgreSQL**, no Supabase or Stripe required.
4. Set a fictional restaurant profile. Visit `/settings`, save a change, `/account` to sign out, and `/sign-in` to return.
5. Optional test payments can be configured later; see `docs/ACCOUNT_BILLING_SETUP.md`.

**Do not use real restaurant/customer records, expose localhost backend endpoints publicly, or delete your Postgres Docker volume.** The application preserves the original v0.7 animated website and synthetic analytics, now with local accounts.
