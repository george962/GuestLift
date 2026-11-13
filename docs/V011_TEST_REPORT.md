# v0.11 verification report — 2026-11-12

Actual checks performed on the artifact in this environment:

- `backend: python -m pytest -q` → **48 passed**, 2 existing httpx deprecation warnings.
- `frontend: npm test` → **42 passed**.
- Global TypeScript `transpileModule` syntax parser → 44 source files parsed, 0 syntax errors (syntax only; not the full TypeScript typecheck).

Not validated here:

- `npm install` and `next build`: required npm dependencies could not be retrieved in this offline execution environment.
- Browser Playwright tests: no running browser and Docker site in this environment.
- Real OpenAI response: no user-supplied OpenAI API key or model.
- Square production OAuth, any live Square/Toast data, Stripe live payments or subscriptions: deliberately disabled.
- Production security review, managed deployment, backup restore, merchant consent, data-processing agreements and real-customer acceptance tests: not performed.

### Mac acceptance commands (run from `~/GuestLift` once patch applied)

```
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose exec -T frontend npm run lint
# optional browser tests after installing Playwright browser binaries:
# docker compose exec -T frontend npm run test:e2e
```

The frontend Docker image uses `npm run start` after Next.js build. Browser E2E tests should be executed on the Mac host against localhost:3000 with Playwright dependencies and browsers installed; run them outside the regular production frontend container when necessary.

Check UI: pricing, connections, analyst empty state, imported data evidence graph, model configured/unconfigured, a question and follow-up, experiments persistence, Stripe test status and customer portal.
