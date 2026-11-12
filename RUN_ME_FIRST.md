# Start TableSignal v0.7 on your Mac

The **full source** must already be inside your existing `~/GuestLift` folder. It keeps the folder name `GuestLift` and your Git repository history; the website is now branded with the provisional name **TableSignal**. You do **not** need to rename the folder.

Copy the **contents** of the downloaded `TableSignal_v0_7` folder into `~/GuestLift` if you have not already done so. Do not copy its `.git` (there isn't one), or erase your existing `.env`.

Then paste this **single complete block** into Terminal:

```bash
cd "$HOME/GuestLift" || exit 1
ls -l frontend/components/landing-experience.tsx
ls -l frontend/app/sign-up/page.tsx
ls -l frontend/app/billing/page.tsx
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose ps
git status
```

Expect: **25 Python tests / 29 Node tests**. Open `http://localhost:3000` and scroll from top to bottom. The public fictional demo works without an account.

To **activate the login form and test checkout**, use `docs/ACCOUNT_BILLING_SETUP.md`. You must create Supabase and Stripe test accounts and enter **your own** keys into the ignored root `.env`; ChatGPT cannot create your external service accounts or obtain your private credentials.

Important: this release **does not process live payments** and must not be used with real restaurant/customer data. Do not expose port 8000 outside localhost or put the backend on public hosting.
