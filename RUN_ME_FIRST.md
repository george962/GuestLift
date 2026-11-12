# GuestLift — Start here

This ZIP contains the **complete source code** for GuestLift v0.1, not just sample pages. Upload the project into the root of your [GuestLift repository](https://github.com/george962/GuestLift).

## What's already built

- Responsive restaurant-software landing page, interactive How It Works page, and Demo dashboard.
- Fabricated Toast-style CSVs, Square API-shaped JSON fixtures, Python adapters, and a proposed GRDC order model.
- SQL persistence + common metrics via FastAPI, an offline browser preview, and seven passing backend tests.
- Docker Compose, CI workflow, docs, source code and task-tracking roadmap.

## How to see something immediately

1. Unzip the package.
2. Double-click **`PREVIEW.html`** for a standalone, offline *design preview*. It has a small interactive Toast/Square browser-only demonstration, but does not run Python or SQL.
3. For the **full site**, follow the local quickstart in [README.md](README.md).

## How to upload to GitHub

For a multi-folder application, the easiest method is to clone your GitHub repository locally, copy the unzipped files into that repository directory (keeping the `frontend/`, `backend/`, and `docs/` folders intact), and commit/push everything. The new README and ROADMAP should **replace** the previous versions.

Alternatively, upload files to GitHub via **Add file → Upload files**. Preserve all folder paths. Do **not** commit `node_modules/`, `.env`, database files, or Python virtual environments.

## What to verify next

- Run backend tests: `cd backend && python -m pytest -q`.
- Run backend server: `cd backend && uvicorn app.main:app --reload --port 8000`.
- Run frontend: `cd frontend && npm install && npm run dev` (requires an internet connection to download packages).
- Open http://localhost:3000/demo. It should display **Local API connected** and persist fixtures when you run an import.
- Repeat the same provider import: it should report duplicates without inflating sales.

**Current limitations:** No live Toast or Square integration, Square Sandbox client, arbitrary file uploads, merchant data, authenticated multi-tenant system, loyalty incrementality or commercial-grade security. See [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md).
