# RUN ME FIRST — GuestLift v0.5

## You already extracted GuestLift into `~/GuestLift`?

**Do not unzip or copy anything again.** From the existing project root:

```bash
cd "$HOME/GuestLift"
grep '"version"' frontend/package.json
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose ps
```

The frontend version should be `0.5.0`. Visit **http://localhost:3000/workspace** and use all sections. You don't need Supabase, Stripe, or an OpenAI API key to explore the public synthetic sandbox.

## You haven't installed v0.5 yet?

Download the complete ZIP, extract it in Finder, and **copy the extracted contents** (folders `frontend/`, `backend/`, `docs/`, and top-level files) into `~/GuestLift/`, choosing to replace older application source files. Keep your `.git/` folder and private `.env` unchanged. You can also `rsync` from your **actual** extracted folder path; do not assume it's inside Downloads or has a particular name. Then use the command block above.

## Working test checklist

- [ ] Homepage shows the new operator-focused hero and interactive example.
- [ ] Workspace Overview computes metrics from fictional Toast/Square orders.
- [ ] Customers shows repeat purchasing and identity coverage.
- [ ] Campaigns switches recorded coupon outcomes and modeled future offer.
- [ ] Ask GuestLift produces evidence-tagged answers.
- [ ] Data Sources links to existing Import Lab; last synthetic import can be loaded into workspace.
- [ ] Pricing explains the proposed subscription without requesting a real card.
- [ ] Account page explains optional Supabase sign-in; no fake account login.

**Safety:** Do not upload real restaurant/customer files and do not publish the backend.
