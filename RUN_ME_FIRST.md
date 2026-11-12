# TableSignal v0.6 — run the current project

If you already placed the v0.6 files inside `~/GuestLift`, **do not unzip anything**. Just copy this entire block into Terminal:

```bash
cd "$HOME/GuestLift" || exit 1
ls -l frontend/components/motion-tour.tsx frontend/app/billing/page.tsx

docker compose up --build -d

docker compose exec -T backend python -m pytest -q

docker compose exec -T frontend npm test

docker compose ps

git status
```

Open http://localhost:3000. The primary product is at `/workspace`. Pricing is `/pricing`, account sign-in is `/sign-in`, and test subscription management is `/billing`. Auth requires explicit Supabase setup; billing requires Stripe test mode. Nothing uploads real merchant data or charges a card.

If `ls` reports missing files, you have not yet copied the contents of the new extracted release folder into your existing `~/GuestLift` project. The `README.md` explains the complete file tree. Do not replace your `.git` directory or `.env` secrets.
