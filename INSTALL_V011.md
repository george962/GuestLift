# Install v0.11 into your existing `~/GuestLift` project

**Do not delete or replace your entire repository.** The upgrade patch contains only changed/new source files, not `.env`/`node_modules`/`.git`/database volumes.

1. Open your local `~/GuestLift` folder in Finder.
2. Place the downloaded `TableSignal_v0_11_Upgrade_Patch.zip` directly in the `GuestLift` folder and extract it **into the same folder**, merging directories and replacing only files with matching names. The ZIP contains no parent folder. Do not extract the `Full_Source` ZIP over your project.
3. Open Terminal and run:

```bash
cd "$HOME/GuestLift" || exit 1
[ -f backend/app/intelligence.py ] || { echo 'v0.11 files are not in the repository root'; exit 1; }
grep '"version"' frontend/package.json
# Use your existing .env; no secrets are included in the patch.
docker compose up --build -d || exit 1
docker compose exec -T backend python -m pytest -q || exit 1
docker compose exec -T frontend npm test || exit 1
docker compose exec -T frontend npm run lint || exit 1
docker compose ps
```

4. Open `http://localhost:3000/analyst`, `http://localhost:3000/pricing` and `http://localhost:3000/connections`.
5. To enable real LLM responses **for synthetic/Square Sandbox data only**, set the following in the existing ignored `~/GuestLift/.env` and restart the backend (`docker compose up -d --force-recreate backend`):

```dotenv
GUESTLIFT_ENABLE_LLM=1
OPENAI_API_KEY=your_own_api_key_here
OPENAI_MODEL=your_supported_model_name_here
```

Never put API secrets in `frontend` `.env` files, browser code, chat messages, GitHub, or screenshots. Confirm `/billing` shows verified Growth test access; otherwise read-only evidence is still accessible but model chat is locked.

**The model uses a real API, not a scripted approximation.** If there is no valid key/model or no imported orders, chat tells you why it's unavailable rather than inventing responses. Typed questions are sent to your configured model provider; don't paste guest personal information.

**Do not use real Square data or live Stripe keys.** These are not enabled in v0.11; see `docs/V011_AI_PRODUCT_AND_FIRST_CUSTOMER.md`.

### If you have already extracted the patch

Skip steps 1–2. Work directly in `~/GuestLift`; there is no Downloads-folder requirement.

### Saving to GitHub after verification

Once the Mac's Docker build and tests pass, inspect changes using `git status -sb` and `GIT_PAGER=cat git diff --stat` before any commit. Check that `.env` is ignored. Do not use `git reset --hard` or remove PostgreSQL volumes.
