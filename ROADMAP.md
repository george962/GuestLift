# GuestLift — Demo-First Development Roadmap

> **Version:** 3.0 (November 12, 2026)  
> **Status:** v0.2 operator-facing prototype; local code and public static-site deployment configuration. No production integrations or real merchant data. See [implementation status](docs/IMPLEMENTATION_STATUS.md).  
> **Goal:** Build a credible, interactive product demo before expanding the research scope.  
> **First sources:** **Toast POS** and **Square POS** (not Squarespace Commerce).  
> **Approach:** Work on **one milestone at a time**. The dates are targets, not deadlines.

## What we're building

**GuestLift** is a vendor-neutral restaurant analytics application. Its first demo will show a restaurant operator how data from two different POS providers moves through provider-specific adapters into one canonical GuestLift Restaurant Data Contract (**GRDC**), then into a database and a shared analytics interface.

**The first promise to demonstrate:** *Different POS inputs. One verified data model. Consistent restaurant reporting.*

Longer-term, GuestLift may support loyalty attribution, experimentation, and incremental contribution profit. The demo **will not** present fabricated marketing lift as real evidence.

**First demo flow:**
1. Choose **Toast Demo** or **Square Demo** on the website.
2. See which test records enter the provider adapter.
3. View the before/after transformation into GRDC orders, items, and payments.
4. See validation results: imported, rejected, and duplicate records.
5. View the same sales and order metrics regardless of the original provider.
6. Click a metric to see the records and rules behind it.

See [Architecture & Demo Storyboard](docs/architecture.md) for the visual system diagram.

## Current product direction (v0.2 — November 12, 2026)

**Restaurant operator journey:** Understand the product on the homepage → choose sample POS data in the pipeline demo → define a coupon/free-item in the Offer Studio (`/offers`) → explore scenario costs and assumptions. Data standardization is the technical foundation; **restaurant promotion intelligence** is the business application we want to validate.

**Implemented in the new package:** revised brand palette with explicit data meanings, professional home/offer flows, fictional-data coupon scenario calculator, line-item audit drilldown, offer math unit tests, public-safe static export option for Cloudflare Pages, and [deployment instructions](docs/DEPLOYMENT.md). The campaign name/code is an editable scenario label **not joined to actual redemptions**. The financial math does **not** estimate additional customer visits or causal profit.

### Immediate public-launch checklist (before starting additional integrations)

- [x] Design a homepage with a concrete operator value proposition and demo CTA.
- [x] Add `frontend/app/offers/page.tsx` with a working browser-only coupon/free-item simulator and assumptions.
- [x] Document colors and visual meanings in `docs/BRAND_SYSTEM.md`.
- [x] Add a static export option and a GitHub-to-Cloudflare deployment walkthrough.
- [x] Add tests for modeled discount/cost calculations.
- [ ] Verify both normal Next.js build and static export build in a network-enabled environment (GitHub CI will check).
- [ ] Deploy the **frontend only** via GitHub-connected Cloudflare Pages and check routes on the public URL.
- [ ] Conduct at least one nontechnical operator walkthrough; record where the product is unclear.
- [ ] Decide on a real custom domain and functioning contact channel before offering a pilot sign-up.

**Do not publish the existing FastAPI API as a public merchant service.** It lacks authentication and has a destructive reset endpoint. The live site must stay fictional-data-only until a security review and proper merchant onboarding exist.

## Current build checkpoint (v0.1)

The downloadable build package adds the website source code, two synthetic-fixture adapters, local SQL persistence, an API, and tests. **Passing Python tests is not equivalent to a hosted, production-ready product.** The frontend still requires install/build/browser verification in a network-enabled environment, and no Square Sandbox credentials have been configured.

- **Implemented and tested:** Toast-style CSV parsing, Square-shaped JSON parsing, common order model, 56 sample orders, SQL idempotent import/replay, aggregate metric API, seven backend tests.
- **Implemented but not verified in browser:** Next.js homepage, How It Works, Demo; offline browser-mode preview, API-connected import interactions.
- **Outstanding:** Real Square Sandbox API client, real Toast integration, arbitrary uploads, customer data security, financial semantics beyond simplified demo, production hosting, pilot feedback.

See [IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md) for detailed completion evidence.

## Milestone overview

| Milestone | Target | Deliverable | Ready when... |
|---|---|---|---|
| **M0 — Story & architecture** | Week 1 | README, short proposal, architecture diagram | Someone understands the product in two minutes |
| **M1 — Clickable website demo** | Week 2 | Home, How It Works, Demo pages | A visitor can explore a clearly labeled *mock* pipeline |
| **M2 — Toast adapter** | Week 3 | Working sample Toast CSV import | CSV test orders normalize correctly and failures are visible |
| **M3 — Square adapter** | Week 4 | Square Sandbox order importer | Square test orders normalize into the **same** GRDC model |
| **M4 — Database & shared reporting** | Week 5 | PostgreSQL + source-independent SQL metrics | Sample financial totals reconcile for both providers |
| **M5 — Connected end-to-end demo** | Weeks 6–7 | Website connected to real pipeline/API | No demo dashboard number is merely hardcoded |
| **M6 — Quality & operator pitch** | Week 8 | Automated tests, demo script, pilot outline | A new reviewer can run and understand the entire demo |

---

## M0 — Story & architecture (do this now)

**Purpose:** Make it easy to explain and show what GuestLift will do. Do not spend this milestone downloading research datasets or building a complete financial model.

- [x] Create the GitHub repository with a README and roadmap. (Recheck file versions after updating.)
- [x] Update `README.md` with **Toast POS + Square POS** and the new demo-first direction.
- [x] Keep a short `docs/proposal.md`: problem, user, goal, sources, approach, deliverables, and constraints.
- [x] Add `docs/architecture.md` with a Mermaid diagram (GitHub rendering to confirm after upload).
- [x] Decide the first **five-minute demonstration**: source choice → ingestion → GRDC → reporting. See `docs/DEMO_SCRIPT.md`.
- [x] Choose the first **three metrics**: order count, net sales, and discounts/refunds (only where sample fields support them). See `docs/METRICS.md`.
- [x] Identify which demo steps are mock screens and which have working code. See `docs/IMPLEMENTATION_STATUS.md`.

**Definition of done:** Another person can open `README.md`, follow the architecture link, and explain what problem we're solving, how Toast/Square reach GuestLift, and what the first product demonstration will show.

**You do not need in M0:** a fictional 10-store brand, a named promotion, 10 failure scenarios, complete vendor field audits, Cafe Rewards/Hillstrom downloads, or formal causal-lift definitions. Those can be added when the relevant feature requires them.

## M1 — Clickable website demo

**Purpose:** Have something visual to show a prospective user *early*, even before the backend exists.

- [ ] Create a Next.js + TypeScript + Tailwind application.
- [ ] Build a simple, professional home page explaining the problem.
- [ ] Build a **How It Works** page with the same architecture diagram and clear stage descriptions.
- [ ] Build a **Demo** page with a Toast/Square source switcher.
- [ ] Show one small, **clearly fictional** record moving through each pipeline stage.
- [ ] Design a small analytics overview with labels for any mock numbers.
- [ ] Make the interface usable on desktop and mobile.

**Definition of done:** A visitor can click through the story without needing to install anything. Mock values are explicitly labeled. Nothing is described as a live merchant connection.

## M2 — Toast adapter

**Purpose:** Replace the Toast side of the mock with working code.

- [ ] Use [Toast's official export field reference](https://doc.toasttab.com/doc/platformguide/adminDataExportFieldReference.html) to create **small synthetic CSV fixtures** for orders, items, and payments.
- [ ] Write a Python adapter to read those files, check expected headers, and normalize the records.
- [ ] Implement the minimum GRDC entities needed: `location`, `order`, `order_item`, `payment`.
- [ ] Output readable validation errors for missing required columns or invalid amounts.
- [ ] Add automated tests for correct counts and repeated imports.
- [ ] Display the adapter's before/after records in the demo.

**Definition of done:** One Toast sample order with multiple items/payments becomes exactly one GRDC order with the expected associated records. The importer doesn't invent missing values.

## M3 — Square adapter

**Purpose:** Prove the common standard works with a genuinely different vendor.

- [ ] Set up a **free Square developer Sandbox** for test orders (do not use live seller data).
- [ ] Use the [Square Orders API](https://developer.squareup.com/reference/square/orders) to create/fetch Sandbox sample orders, or use saved Sandbox JSON fixtures while developing.
- [ ] Write a Python Square adapter that produces the **same GRDC entities** as Toast.
- [ ] Reuse the same canonical validation and metric rules—no Square-specific SQL reporting.
- [ ] Test a multi-item order, payment status, and absent optional fields.
- [ ] Add a Square-specific before/after transformation view.

**Definition of done:** Sample Square and Toast orders both pass the same GRDC validations, and unsupported fields are shown as *unknown* rather than silently guessed.

## M4 — Database & shared reporting

**Purpose:** Demonstrate that our standard supports trusted, provider-independent analytics.

- [ ] Create PostgreSQL tables and migrations for the minimal canonical entities plus `import_runs`.
- [ ] Persist Toast and Square normalized records with source lineage.
- [ ] Make repeated imports idempotent so the same records are not double-counted.
- [ ] Implement **order count**, **net sales**, and **discount/refund totals** with explicit metric definitions.
- [ ] Reconcile test fixture totals to the cent; separate unavailable financial fields from zero.
- [ ] Build FastAPI endpoints returning import status and computed metrics.

**Definition of done:** Both sources use the same SQL metric logic, and every displayed number can be traced to test records. Financial totals are checked rather than assumed.

## M5 — Connected end-to-end demo

**Purpose:** Turn the website into a functioning product demonstration.

- [ ] Connect Next.js to the FastAPI backend.
- [ ] Replace mock pipeline stage results with actual adapter and database output.
- [ ] Let a user select a provided sample, run an import, and inspect transformations.
- [ ] Show import validation results, order-level drill-down, and consistent metrics.
- [ ] Add understandable loading, empty, failed, and duplicate-import states.
- [ ] Create a short narrated walk-through (script or screen recording).

**Definition of done:** A new reviewer can run the prescribed demo and verify that numbers update from actual imported test data, not a hardcoded dashboard.

## M6 — Quality & operator pitch

**Purpose:** Make the system dependable enough to demonstrate professionally.

- [ ] Run unit and integration tests through pytest and GitHub Actions.
- [ ] Test missing columns, duplicate orders, one-to-many joins, missing payments, and refunds.
- [ ] Package local services using Docker Compose and document the quickstart.
- [ ] Show clear demo-only/data-origin disclaimers; never request real payment card numbers.
- [ ] Create a one-page operator pitch: what problem this solves, what it shows today, and what a real pilot would require.
- [ ] Ask at least one operator/technical reviewer for feedback and record what to improve.

**Definition of done:** A reviewer can reproduce the demo, understand limitations, and identify what merchant permission/data is needed for a future real pilot.

---

## Later, only when needed

- **Loyalty/incrementality:** Add campaign assignments, loyalty events, experiments, and real contribution-margin calculations once there is an actual campaign-evaluation feature. [Cafe Rewards Offers](https://mavenanalytics.io/data-playground/cafe-rewards-offers) can support synthetic event processing; [Hillstrom](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html) can test statistical methods, but neither proves restaurant ROI.
- **More sources:** Add another POS or ordering provider only after Toast and Square work against GRDC.
- **Production integrations:** Merchant authorization, vendor permissions, security, identity mapping, operations, and data governance require a separate pilot-readiness phase.
- **Advanced scale:** Performance benchmarks and cloud deployment matter once the minimal pipeline works reliably; don't add infrastructure for appearance alone.

## Working agreement for this project

1. Complete **one milestone** at a time.
2. Ask ChatGPT for **complete files**, not tiny disconnected patches.
3. Verify each deliverable against its **Definition of Done**.
4. Commit meaningful checkpoints to GitHub and update the checkboxes.
5. Keep **public mock data**, **Square Sandbox data**, and **real merchant data** clearly distinguished.
