#!/usr/bin/env python3
"""Safe, in-place TableSignal v0.12.2 repository consistency/CI baseline.

No deletes, Git commands with side effects, database changes, downloads, or secret reads.
Run from project root: python3 repair_tablesignal.py
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
VERSION = '0.12.2'
PRICE = '$99 per selected monitored location per month (proposed; not live)'

if not (ROOT / '.git').exists() or not (ROOT / 'compose.yaml').is_file():
    raise SystemExit('Run this script in the existing ~/GuestLift Git repository.')
for path in ('frontend/package.json', 'frontend/package-lock.json', 'backend/app/main.py',
             'frontend/app/pricing/page.tsx', 'ROADMAP.md', 'README.md',
             'docs/V013_TO_V1_PRODUCTION_GATES.md'):
    if not (ROOT / path).is_file():
        raise SystemExit(f'Missing essential source file: {path}; restore it before patching.')

backup = Path.home() / 'TableSignal-backups' / ('readiness-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
changes: dict[str, str] = {}

def original(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')

def replace_exact(path: str, old: str, new: str, *, required: bool = True) -> None:
    src = changes.get(path, original(path))
    if old in src:
        changes[path] = src.replace(old, new)
    elif new not in src and required:
        raise SystemExit(f'Refusing ambiguous modification to {path}: expected text missing: {old[:85]!r}')

# Synchronize ALL declared application version sources without rewriting lockfile metadata.
replace_exact('frontend/package.json', '"version": "0.11.0"', f'"version": "{VERSION}"')
lockpath = 'frontend/package-lock.json'
locktext = original(lockpath)
if locktext.count('"version": "0.10.0"') < 2 and f'"version": "{VERSION}"' not in locktext:
    raise SystemExit('Unknown package-lock root version; inspect manually before modifying.')
# Only the top-level and packages[""] version fields; never rewrite dependency versions.
changes[lockpath] = re.sub(r'"version": "0\.10\.0"', f'"version": "{VERSION}"', locktext, count=2)
replace_exact('backend/app/main.py', "version='0.11.0'", f"version='{VERSION}'")

# Distinguish proposed commercial pricing from Stripe TEST price (provider-configured).
pricing = 'frontend/app/pricing/page.tsx'
replace_exact(pricing,
    'Your current $149 Stripe Sandbox Growth checkout is a test subscription, not a real payment.',
    'The local Stripe TEST checkout is not a real payment; its price is determined by the configured Stripe TEST Price ID, not by the proposed commercial price.')
replace_exact(pricing,
    "['Your own connected POS data','No','One location; supported provider']",
    "['Your own connected POS data','No','Authorized, selected locations after production launch']")

# Resolve the old roadmap link by replacing the superseded milestone presentation.
changes['ROADMAP.md'] = '''# TableSignal roadmap — v0.12.2 integration baseline

**Status: local developer preview, not production-ready.** Updated 2026-11-22.

## Product direction

**Connect → Discover → Investigate → Decide → Track.** A restaurant operator sees evidence-linked changes in orders, identified guests and promotion spending, investigates uncertainty, saves a decision and revisits the outcome. Do not promise causal lift without an appropriate experiment.

## Current capabilities (source exists; external operation needs verification)

- Next.js marketing site, synthetic sample workspace, animated walkthrough, sign-up/sign-in, onboarding, analyst, connection and billing screens.
- FastAPI, PostgreSQL local account/session prototype, Square Sandbox integration code, Stripe TEST subscription scaffolding, and evidence-based analytical functions.
- Pure provider-location billing quote rules and unit tests exist **but are NOT integrated** with authenticated location selection, entitlements, ingestion, or Stripe checkout.
- Existing ZIP archives and dated milestone docs are historical artifacts, **not an installation method or evidence of release readiness**.

## Current acceptance priorities (in order)

1. Pass automated CI: Node tests, TypeScript, Next production build, Python tests, browser smoke, and secret scanning on the *same* commit.
2. Test end-to-end: sign up → verify session/onboarding → authorize own Square Sandbox → sync synthetic orders → isolated analysis → Stripe TEST checkout → reconcile → cancel.
3. Eliminate public/demo reset and untrusted-upload paths from any hosted configuration; move to a production identity and tenant isolation model.
4. Build and test *server-derived* canonical location entitlements, scoped data access, and Stripe quantity/invoice reconciliation. No paid-location claims before this.
5. Stage with HTTPS, migrations, managed secrets/DB/backups, monitoring, incident and support processes, terms and privacy consent.
6. Pilot with one consenting Square merchant after the relevant security gates pass; measure whether the recurring workflow changes a real decision.

## Commercial assumptions (not active billing)

- Growth **$99/selected monitored location/month**, provisional. This is **not** the Stripe TEST price: TEST amounts come from `STRIPE_GROWTH_PRICE_ID`.
- A proposed 14-day no-card trial starts only after first verified healthy sync; **not implemented**.
- Square production OAuth and Stripe LIVE are **disabled / unverified**. Toast production support is out of scope for the first launch.

## Launch gate references

- [Production readiness status and evidence](docs/PRODUCTION_READINESS.md) — authoritative pass/fail checklist.
- [Full v0.13→v1.0 acceptance criteria](docs/V013_TO_V1_PRODUCTION_GATES.md).
- [Location, signup and pricing design](docs/V012_PRODUCT_AND_SELF_SERVICE_BILLING.md).

Do not enable real merchant data or payments until all applicable gates have independently verified evidence and owner approval.
'''

changes['README.md'] = '''# TableSignal — v0.12.2

**Restaurant decision intelligence: Connect → Discover → Investigate → Decide → Track.**

TableSignal is a **local development preview**, not a commercially deployed restaurant analytics service. The public workspace uses fictional data. Private accounts are developer-only; the Square connector targets **Square Sandbox**; Stripe supports **TEST** billing only. Never use this build for real merchant data, public customer signups, or live payments.

## Repository layout

- `frontend/` — Next.js public site, sample workspace, local-account UI, analyst, Square connection and billing screens.
- `backend/` — FastAPI, synthetic order adapters, local auth, SQLite/PostgreSQL-friendly models, Square Sandbox and Stripe TEST logic.
- `docs/` — current product/launch specifications and [production readiness](docs/PRODUCTION_READINESS.md).
- `compose.yaml` — **localhost-only** developer services and retained Postgres volume.

## Local development

1. Use Docker Desktop and keep `.env` local; never commit credentials.
2. From repository root: `docker compose up -d --build`.
3. Open `http://localhost:3000`; test API health at `http://localhost:8000/api/health`.
4. Run `docker compose ps -a` and `docker compose logs --tail=100 frontend backend` if startup fails.
5. Never run `docker compose down -v` unless intentionally destroying local database contents.

## Tests

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
# with localhost:3000 serving: npx playwright test e2e/v012-public.spec.ts
cd ../backend
python -m pip install -r requirements.txt
python -m pytest -q
PYTHONPATH=. python -m unittest discover -s tests -p 'test_location_billing_rules.py' -v
```

CI on pull requests must run the same checks. A successful build or synthetic sample test **does not** certify security, real Square API behavior, or Stripe LIVE readiness.

## Current commercial assumption

Growth is **provisionally $99 per selected, eligible, provider-verified location per month**. This is a product proposal, **not active pricing**. Stripe TEST uses its independently configured `STRIPE_GROWTH_PRICE_ID` and its quantity is **currently fixed to one**. The standalone `backend/app/location_billing_rules.py` quote is **not wired** to checkout or entitlements; production billing is blocked until it is.

## Source of truth

- [Active roadmap](ROADMAP.md)
- [Production readiness gates and evidence log](docs/PRODUCTION_READINESS.md)
- [Detailed v0.13→v1.0 release gates](docs/V013_TO_V1_PRODUCTION_GATES.md)
- [Product and location billing specification](docs/V012_PRODUCT_AND_SELF_SERVICE_BILLING.md)

Earlier `INSTALL_V0*`, `README_V011.md`, preview HTML files and tracked ZIP releases are **historical artifacts**. Do not unzip patches over the live working tree. Use version-controlled edits, branches, pull requests and CI.
'''

# Retire stale GitHub-main-as-v0.10 assessment without asserting new validation.
replace_exact('docs/V013_TO_V1_PRODUCTION_GATES.md',
    'Reconcile v0.11 Mac workspace with `george962/GuestLift` main, which as inspected on 2026-11-12 reports v0.10. Verify full file inventory, tests and migrations before applying website updates.',
    'Reconcile the actual deployed source and local v0.12.2 working tree with GitHub main, including uncommitted homepage edits. Validate complete file inventory, automated checks, migrations and deployed commit identity before release.')

# Guard the most destructive *unauthenticated* development endpoint by an explicit
# opt-in flag. Keep default disabled and do not auto-opt-in even in docker compose.
main_path = 'backend/app/main.py'
main_src = changes.get(main_path, original(main_path))
if "TABLESIGNAL_ENABLE_DEMO_RESET" not in main_src:
    old = "@app.post('/api/reset')\ndef reset():\n    reset_db()"
    new = "@app.post('/api/reset')\ndef reset():\n    # Never enable this unauthenticated fixture reset on hosted deployments.\n    import os\n    if os.getenv('TABLESIGNAL_ENABLE_DEMO_RESET') != '1':\n        raise HTTPException(status_code=404, detail='Demo reset is disabled.')\n    reset_db()"
    if old not in main_src:
        raise SystemExit('Cannot locate exact /api/reset implementation; no files changed.')
    changes[main_path] = main_src.replace(old, new)

# Preserve existing pipeline test behavior only inside the test process.
testpath = 'backend/tests/test_pipeline.py'
tests = original(testpath)
if "TABLESIGNAL_ENABLE_DEMO_RESET" not in tests:
    old = "        assert client.post('/api/reset').json()['status']=='reset'"
    new = "        monkeypatch.setenv('TABLESIGNAL_ENABLE_DEMO_RESET', '1')\n        assert client.post('/api/reset').json()['status']=='reset'\n        monkeypatch.delenv('TABLESIGNAL_ENABLE_DEMO_RESET', raising=False)"
    if old not in tests:
        raise SystemExit('Cannot locate /api/reset test; no files changed.')
    changes[testpath] = tests.replace(old, new)

# Guard against accidental re-commit of generated archives and secrets.
ignore = '.gitignore'
ignore_src = original(ignore)
extra = '''
# Distributable packages are generated from Git, not committed to main.
*.zip
*.tar
*.tar.gz
# Sensitive local credentials and tooling output
.env.*
!.env.example
!.env.sample
.playwright/
playwright-report/
test-results/
coverage/
.pytest_cache/
'''
if '# Distributable packages are generated from Git' not in ignore_src:
    changes[ignore] = ignore_src.rstrip() + '\n' + extra

changes['docs/PRODUCTION_READINESS.md'] = '''# TableSignal production readiness — evidence log

**Version:** v0.12.2 local developer preview. **Last reviewed:** 2026-11-22. **Launch decision: BLOCKED.**

This is the **status board** for [the complete v0.13→v1.0 gates](V013_TO_V1_PRODUCTION_GATES.md). Do not mark a gate passed on code presence alone. Each gate needs a linked CI run, recorded test case or evidence artifact, accountable owner and sign-off date.

| Gate | Status | Verified evidence to collect | Release owner |
|---|---|---|---|
| A. Source and CI | NOT VERIFIED | CI runs Node/TS/Next/Python/browser + secret scan on exact commit; branch protections, dependency policy, rollback | Engineering |
| B. Identity and tenancy | BLOCKED | Hosted email verification/recovery, org roles, adversarial isolation tests, secret manager, privacy and legal review | Security/engineering |
| C. Square production | BLOCKED | Consented production OAuth, token lifecycle, webhook/sync resilience, reconciliation against source exports | Integrations |
| D. AI evidence | NOT VERIFIED | Tenant-scoped sanitized aggregates, prompt-injection tests, evidence and rate-limit evaluations | Data/ML |
| E. Location billing | BLOCKED | Server-owned eligible location selection → entitlements → location-scoped ingestion → Stripe quantity/webhook/proration tests | Billing |
| F. Customer usability | NOT VERIFIED | Uncoached onboarding and accessible mobile E2E with at least one qualified pilot operator | Product |
| G. Operational launch | BLOCKED | HTTPS staging, migrations, backup/restore, monitoring/alerts, incident/support and an authorized LIVE billing test | Operations |

## Important verified implementation limitations

- The `location_billing_rules.py` class and quote tests are **pure domain code**, not an authenticated API or entitlement service. Do not expose its output as a real Stripe billing quantity.
- Current Stripe TEST checkout uses **`quantity: 1`** and a configured TEST price. No verified recurring location metering, entitlements, live invoices or prorations exist.
- Current `local_auth.py` explicitly documents **local development only** and lacks production email verification/recovery and operational access controls.
- `frontend/lib/supabase-client.ts` is a **compatibility alias** for `local-auth.ts`, not a second active Supabase identity provider. Remove the alias only after checking all imports and browser flows.
- `backend/app/dev_admin.py` and `dev_reset_password.py` are **local console utilities**, not exposed admin HTTP endpoints. Reset CLI is opt-in; protect workstation and backend access. Separately, `POST /api/reset` was a publicly addressable local-demo HTTP reset and is now **disabled unless `TABLESIGNAL_ENABLE_DEMO_RESET=1`**. Do not set that flag on any hosted deployment.
- Other demo imports/uploads, campaigns, fixture-only metrics and test-account endpoints are not authenticated production SaaS services. They require explicit isolation or removal before deployment.
- Existing sample reports and test counts cannot establish Square production authorization, financial completeness, causal profit, secure hosting or commercial readiness.

## Next implementation sequence (must follow in this order)

1. **Clean source & tests:** merge reviewed baseline PR, ensure CI green, inspect dependency vulnerabilities, adopt branch protection + CODEOWNERS, set release tags, create staging environment isolated from development.
2. **Identity first:** choose a supported production auth provider or implement audited production auth with verified email, reliable recovery, session/CSRF protections, organization roles and complete tenant isolation tests. Keep sample mode separate.
3. **Square ingestion:** implement approved production OAuth, per-merchant location discovery and secure token lifecycle; durable scheduled data refresh, backfills, refunds/discount reconciliation, health alerts, consent, delete and revoke paths.
4. **Server-backed entitlements:** persist eligible canonical locations authorized per workspace; enforce selected locations at ingestion, dashboard, exports and AI tool boundaries. Add authenticated quote/confirm endpoints and reconcile Stripe TEST line-item quantities **from these persisted entitlements**.
5. **TEST to LIVE billing:** validate every subscription change, signature, webhook retry, tax, trial, invoice, failure and cancellation. Enable Stripe LIVE only behind a separate reviewed deployment and explicit owner approval.
6. **Pilot evidence:** at least one consented operator completes Detect → Investigate → Decide → Track repeatedly and can describe the value; support and privacy operations exercised.

## Evidence record template

`Gate | criterion | owner | exact commit | test/screenshot/log link | date | pass/fail | reviewer | remaining risks`

A checked box is not evidence. Do not promote this preview to production or ingest actual merchant data until **all applicable** gates are PASS with owner sign-off.
'''

changes['.github/workflows/ci.yml'] = '''name: Source verification

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  frontend:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci --no-audit --no-fund
      - run: npm test
      - run: npm run lint
      - run: npm run build
      - name: Browser smoke — public fictional homepage
        run: |
          npx playwright install --with-deps chromium
          npm run start -- --port 3000 > /tmp/tablesignal-next.log 2>&1 &
          for i in $(seq 1 30); do
            if curl -fsS http://127.0.0.1:3000/ >/dev/null; then break; fi
            sleep 2
          done
          npx playwright test e2e/v012-public.spec.ts

  backend:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: backend/requirements.txt
      - run: python -m pip install -r requirements.txt
      - run: python -m pytest -q
      - run: PYTHONPATH=. python -m unittest discover -s tests -p 'test_location_billing_rules.py' -v

  secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
'''

# Validate all modifications before writing any file.
for rel, new in changes.items():
    if not isinstance(new, str) or not new.strip():
        raise SystemExit(f'Invalid replacement: {rel}')
    if rel.startswith('/') or '..' in Path(rel).parts:
        raise SystemExit(f'Unsafe path: {rel}')

# Print a useful concise diff preview of existing files.
print('TableSignal v0.12.2 integration cleanup')
print('Working directory:', ROOT)
print('Files to write:', len(changes))
for rel, updated in changes.items():
    old = (ROOT / rel).read_text(encoding='utf-8') if (ROOT / rel).is_file() else ''
    if old != updated:
        print('  ', 'MODIFY' if old else 'CREATE', rel)

for rel, new in changes.items():
    target = ROOT / rel
    old = target.read_text(encoding='utf-8') if target.is_file() else None
    if old == new:
        continue
    if old is not None:
        destination = backup / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new, encoding='utf-8')

print('\nDone. Backups:', backup)
print('Your v0.12.2 homepage component and CSS were NOT touched.')
print('No Git commit, push, Docker action, .env or database changes were made.')
