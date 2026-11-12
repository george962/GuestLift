# GuestLift — Project Roadmap & Build Checklist

> **Version:** 2.1 · **Updated:** November 12, 2026  
> **Status:** Planning / not yet implemented  
> **Format:** 8-week independent capstone; adjust the calendar as needed, but keep the milestone gates.  
> **Target budget:** $0 for local development; hosting and real integrations are optional later.  
> **Initial market:** Fast-casual restaurant groups with roughly 5–50 locations.  
> **Initial integrations:** **Toast POS** and **Squarespace Commerce** (**not Square POS**).  
> **Core architecture:** Vendor adapters → **GuestLift Restaurant Data Contract (GRDC)** → validated PostgreSQL data → analytics/experimentation → API → web app.

## How to use this document

1. Put this file at the root of the GitHub repository as **`ROADMAP.md`**.
2. Work **top to bottom**. Each unchecked `- [ ]` is a task you can turn into a GitHub Issue.
3. Do not mark a milestone complete until every **Definition of Done** requirement passes.
4. Record decisions and evidence in `docs/`; commit tests and fixtures with the code.
5. Update the checkboxes as you go. GitHub renders them as an actionable checklist.
6. Keep **academic prototype**, **commercial product**, and **real restaurant pilot** claims separate.

### Milestone index

| Milestone | Target | Points | Status | Primary output |
|---|---|---:|---|---|
| [M0 — Proposal & source feasibility](#m0--proposal--source-feasibility-week-1--10-points) | Week 1 | 10 | ☐ | Business case and source inventory |
| [M1 — GuestLift data standard](#m1--guestlift-data-standard-week-2--20-points) | Week 2 | 20 | ☐ | GRDC v0.1.0 schema and tests |
| [M2 — Toast & Squarespace adapters](#m2--toast--squarespace-adapters-weeks-34--20-points) | Weeks 3–4 | 20 | ☐ | Two reliable format importers |
| [M3 — Multi-location SQL analytics](#m3--multi-location-sql-analytics-week-5--15-points) | Week 5 | 15 | ☐ | Reconciled, provider-neutral metrics |
| [M4 — Incrementality & campaign economics](#m4--incrementality--campaign-economics-week-6--15-points) | Week 6 | 15 | ☐ | Experiment analysis with limitations |
| [M5 — Website & operator workflow](#m5--website--operator-workflow-week-7--10-points) | Week 7 | 10 | ☐ | Working operator-facing demo |
| [M6 — Reliability, scale & pilot-readiness](#m6--reliability-scale--pilot-readiness-week-8--10-points) | Week 8 | 10 | ☐ | Tested, documented final demo |
| **Total** | | **100** | | |

---

## 1. Business problem, customers, and scope

### Business question

**For a multi-location restaurant group, which loyalty and promotional campaigns produce *incremental contribution profit*, and how should the operator change future promotions across locations?**

The first demo concerns a **fictional 10-location fast-casual chain** running a promotion. GuestLift must show what happened, how trustworthy the data is, what can be estimated from a valid experiment, and when there is **insufficient evidence** to conclude anything.

### Primary users

- Director of Marketing / Loyalty: “Which campaigns should we repeat or change?”
- CRM / Retention Manager: “Which customers participated, and did the promotion change behavior?”
- Operations / Finance Manager: “How did margin, discounts, refunds, and location differences affect results?”

### Product differentiator to test

**Interoperability + defensible business metrics.** POS/commerce integrations should normalize into the same open, versioned GuestLift contract so that source-specific parsing never changes the metric logic. This is a **hypothesis**, not a proven advantage over Bikky, Thanx, Toast, or other vendors.

### Explicit non-goals for v1

- [ ] Acknowledge that we are **not** building a payment processor, issuing loyalty points, or accessing card numbers.
- [ ] Acknowledge that a POS export **alone cannot prove causal uplift** or actual incremental profit.
- [ ] Acknowledge that data generated for a demo is **not evidence** that a restaurant's promotion worked.
- [ ] Keep live merchant integrations, multi-tenant commercial security, Amex/Chase partnerships, and advanced ML out of initial required scope.
- [ ] Do **not** call GRDC an adopted industry standard; it begins as a **proposed open specification**.

---

## 2. Where the data comes from

**Important:** No public dataset supplies a complete real multi-location restaurant promotion experiment with actual POS transactions, customer identifiers, treatments, and contribution costs. **Use different sources for different technical claims.**

| Source | URL / acquisition | Use in GuestLift | May we claim real restaurant ROI? |
|---|---|---|---|
| Toast **published field definitions** | [Toast Data Export Field Reference](https://doc.toasttab.com/doc/platformguide/adminDataExportFieldReference.html), [export overview](https://doc.toasttab.com/doc/platformguide/adminDataExportOverview.html) | Specify mock `OrderDetails.csv`, `ItemSelectionDetails.csv`, and `PaymentDetails.csv` and build adapter tests | **No** — documentation is not transaction data |
| Squarespace Commerce **published CSV/API definitions** | [Order CSV guide](https://support.squarespace.com/hc/en-us/articles/206540677-Export-Commerce-orders), [Commerce APIs](https://developers.squarespace.com/commerce-apis/overview) | Specify mock multiline order CSV, update scenarios, and adapter tests | **No** — documentation is not merchant data |
| **Cafe Rewards Offers** | [Maven Analytics Data Playground](https://mavenanalytics.io/data-playground/cafe-rewards-offers) | Practice event ingestion and offer-received/viewed/completed reporting | **No** — simulated marketing activity |
| **Hillstrom email experiment** | [MineThatData original project](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html) | Validate randomized treatment/control analysis | **No restaurant-specific claim** — historic apparel experiment |
| **Seeded restaurant generator** | We build it | 10+ locations, menu items, orders, promotions, costs, errors, refunds, load tests | **No** — generated data |
| **Future merchant-authorized data** | Voluntary, formally permitted pilot | Actual operator analysis with private exports, assignment logs, costs | **Only when experimental design and data justify it** |

### Data-acquisition checklist

- [ ] Record the original source link, download/access date, applicable license, and expected file format for each source in `docs/source-inventory.md`.
- [ ] Inspect **actual downloaded files** before writing a parser; do not assume the example column list is exhaustive.
- [ ] Save raw public datasets under `data/raw/` locally and add this directory to `.gitignore` (unless its license and size explicitly justify committing a sample).
- [ ] Store only **small, fabricated** examples under `tests/fixtures/` in Git.
- [ ] Record provenance for every data run: `mock_vendor_fixture`, `public_synthetic`, `public_randomized_nonrestaurant`, `generated_scale_test`, or `merchant_authorized`.
- [ ] Document which required fields **cannot** be obtained from standard Toast/Squarespace exports (e.g., randomized assignment logs and item-level COGS may need separate systems).
- [ ] Identify export/API access restrictions and format drift risk; do not claim that merchant access is guaranteed.

### Vendor-specific caveats to implement

- **Toast:** orders, item selections, and payments can be different files and grains; column selection/order may be customized; a restaurant business day is not always a calendar date.
- **Squarespace Commerce:** a multiline order export can place header fields only on the first row; automatically exported prior orders may not update when status/refund changes; it is a commerce source, **not** a full restaurant POS replacement.
- **Square POS** is a separate provider and is **not** one of our first two adapters. Add it only after both required adapters pass.

---

## 3. Technology decisions and development environment

| Layer | Required tools | Intended job |
|---|---|---|
| Repository & editor | Git, GitHub, VS Code | Source control, issues, reviews |
| Core language | Python 3.12+ | Importers, domain logic, analysis |
| Source formats | Python `csv`, Pydantic, PyYAML, `jsonschema` | Parse, map, validate against GRDC |
| Data analysis | Pandas, NumPy, SciPy / statsmodels | EDA, experimental estimates |
| Data storage | PostgreSQL | Canonical relational data and import audit |
| DB access & migrations | SQLAlchemy + Alembic | Reliable queries and schema evolution |
| Backend | FastAPI | Typed endpoints for imports and analytics |
| Frontend | Next.js, TypeScript, Tailwind CSS, Recharts | Landing page and operator-facing product |
| Tests | pytest + GitHub Actions | Contract, unit, integration, regression, CI |
| Local services | Docker Compose | Repeatable application environment |
| Optional later | dbt Core, scikit-learn, job scheduler, cloud hosting | Only where a concrete need is demonstrated |

**Do not add** Kafka, Kubernetes, Azure/AWS, complicated agents, streaming, or a full ML stack solely to make the GitHub README look more advanced.

### Proposed repository layout

```text
guestlift/
├── README.md                          # Project elevator pitch + quickstart
├── ROADMAP.md                         # This checklist
├── .gitignore
├── .env.example                       # Example configuration, NO secrets
├── .github/
│   └── workflows/                     # CI
├── docs/
│   ├── proposal.md
│   ├── source-inventory.md
│   ├── data-feasibility.md
│   ├── architecture.md
│   ├── metric-definitions.md
│   ├── security-and-privacy.md
│   ├── decisions/                     # Architecture decision records
│   ├── benchmarks.md
│   └── pilot-plan.md
├── contracts/
│   └── grdc/
│       └── 0.1.0/
│           ├── README.md
│           ├── CHANGELOG.md
│           ├── schemas/               # Canonical JSON Schemas
│           ├── examples/              # Valid and invalid examples
│           └── provider-mappings/
│               ├── toast_csv/
│               └── squarespace_commerce_csv/
├── backend/
│   ├── app/
│   │   ├── adapters/{toast,squarespace}/
│   │   ├── ingestion/
│   │   ├── domain/
│   │   ├── analytics/
│   │   └── api/
│   ├── migrations/
│   └── pyproject.toml
├── frontend/                           # Next.js application
├── sql/                                # Metric SQL and views
├── scripts/                            # Local data generation / import
├── data/                               # Raw downloaded data (gitignored)
├── tests/
│   ├── fixtures/{toast,squarespace,generated}/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   └── performance/
└── compose.yaml                        # Local PostgreSQL/backend/frontend
```

### Global engineering rules

- [ ] All money calculations use **integer minor currency units** (cents), never binary floats.
- [ ] Keep `NULL`/unknown separate from observed zero.
- [ ] Every source record has provider, account/location scope, external ID, ingest timestamp, and lineage.
- [ ] Source files are immutable or content-addressed; track checksum + import run.
- [ ] Re-importing a file must be idempotent; corrections/refunds must not create duplicate sales.
- [ ] Distinguish order, item, payment, and refund grains; never multiply revenue through joins.
- [ ] Model UTC timestamps and local restaurant business dates explicitly.
- [ ] Allow anonymous orders; do not fabricate a customer identifier to force joins.
- [ ] Keep randomized experiment assignments separate from campaign views and redemptions.
- [ ] Every metric defines its numerator, denominator, exclusions, window, and source requirements.
- [ ] Never represent test fixtures or synthetic analysis as results from a real restaurant.

---

## 4. What our standard means: GRDC v0.1.0

**GRDC = GuestLift Restaurant Data Contract.** It is the provider-neutral format that adapters produce, stored and validated independently from Toast/Squarespace source formats.

### Initial canonical entities

| Entity | Grain | What must be represented |
|---|---|---|
| `organizations` | One restaurant business/tenant | Organization ID and isolation |
| `locations` | One location | Organization link, source mapping, time zone |
| `orders` | One source order in an account/location | Stable scoped source ID, date/time, currency, status |
| `order_items` | One item line | Order link, quantity, monetary fields, optional SKU |
| `payments` | One payment event | Order link, payment event ID, amount, status (no card PAN) |
| `refunds` | One refund event | Source refund ID, amount, order, event time |
| `customers` / `customer_aliases` | One pseudonymous customer + source aliases | Match provenance; unknown is permitted |
| `campaigns` | One campaign definition | Campaign, eligible population, effective period, costs where known |
| `assignments` | One pre-treatment experiment assignment | Randomized arm, unit ID, timestamp, experiment ID |
| `exposures` / `reward_events` | One offer exposure or redemption event | Event ID/type/time and campaign reference |
| `costs` | One dated cost assumption/source | Variable cost, reward cost, confidence/availability |
| `import_runs` / `exceptions` | One job or quality event | Checksums, accepted/rejected counts, error reason |

### Versioning policy

- `0.1.0` is a **draft** reference contract; publish docs and tests before calling it stable.
- Adding a compatible optional field should not break older valid fixtures.
- Removing or redefining a required field needs explicit versioning and migration review.
- Provider adapters must declare the GRDC version they output.
- An external developer should be able to produce conforming GRDC JSON without reading GuestLift source code.

---

# 5. Milestones and completion criteria

## M0 — Proposal & source feasibility (Week 1 · 10 points)

**Goal:** Define one financially relevant marketing decision and prove the required input formats and sample datasets exist.

### Tasks

- [ ] Create the GitHub repository and add this `ROADMAP.md`.
- [ ] Create a short `README.md` (problem, target user, demo-only disclaimer, planned stack, roadmap link).
- [ ] Write `docs/proposal.md` in the style of a BU project proposal: problem, objectives, data sources, methodology, expected outcomes, constraints.
- [ ] Specify the initial **fictional chain** (10 fast-casual locations), primary decision-maker, and one promotion to analyze.
- [ ] Define what you mean by *incremental visits*, *incremental revenue*, and *incremental contribution profit*.
- [ ] Review Toast's official export definitions; document each relevant file's grain and candidate keys.
- [ ] Review Squarespace's official order CSV fields; document multi-line rows and change/update limitations.
- [ ] Download/inspect Cafe Rewards and Hillstrom; record their actual schemas, row counts, license, and limitations.
- [ ] Complete a field capability table: available from Toast / Squarespace / additional merchant sources / generated only.
- [ ] Draw a first high-level dataflow diagram (provider adapters → GRDC → PostgreSQL → analytics → API → UI).
- [ ] List at least **10** potential import or financial correctness failures.
- [ ] Record at least three uncertainties/risks that would block a real customer pilot.

**Files to submit**

- `docs/proposal.md`
- `docs/source-inventory.md`
- `docs/data-feasibility.md`
- `docs/architecture.md` (initial diagram)
- Repository `README.md`

**Definition of Done / Gate**

- [ ] Toast and Squarespace are treated as **different types of sources**, with no false assumption of complete restaurant data.
- [ ] Every planned analysis has a data source or is clearly labeled as unobservable until a pilot.
- [ ] The proposed demonstration includes no unsupported claims about causal restaurant profit.
- [ ] M0 receives at least **8/10** on review, with no critical uncorrected assumptions.

**Review questions:** What is the grain of each file? What does the source identify as a paid order? Where do variable costs come from? What proves that the marketing assignment was randomized?

---

## M1 — GuestLift data standard (Week 2 · 20 points)

**Goal:** Create a well-defined contract that both vendor adapters can emit without changing meaning.

### Tasks

- [ ] Write `contracts/grdc/0.1.0/README.md`: motivation, required concepts, field-level definitions, examples.
- [ ] Draw an ER diagram for organizations, locations, orders, items, payments, refunds, and audit records.
- [ ] Define scoped identity strategy: `(tenant, provider, source_account, source_location, external_order_id)`.
- [ ] Document order vs. item vs. payment vs. refund **grain** and allowed one-to-many relationships.
- [ ] Specify `amount_minor` + currency code and a complete **null semantics** policy.
- [ ] Define order status transitions and what happens with delayed updates/revised source exports.
- [ ] Define timestamp conventions: UTC, source zone, local business day.
- [ ] Write JSON Schemas for at least `order`, `order_item`, `payment`, `refund`, `campaign_assignment`.
- [ ] Create at least one valid and one deliberately invalid fixture for each schema.
- [ ] Document Toast → GRDC and Squarespace → GRDC field mappings, including unmappable fields.
- [ ] Create `CHANGELOG.md`, version compatibility rules, and adapter version metadata.
- [ ] Implement automated JSON Schema validation with `pytest` + `jsonschema`.
- [ ] Make a test explicitly reject a missing required field and an impossible currency/amount value.
- [ ] Make a test confirm optional missing data is **unknown**, never silently set to zero.

**Files to submit**

- `contracts/grdc/0.1.0/README.md` and `CHANGELOG.md`
- `contracts/grdc/0.1.0/schemas/*.schema.json`
- `contracts/grdc/0.1.0/examples/`
- `contracts/grdc/0.1.0/provider-mappings/`
- `docs/architecture.md` (ER diagram), `docs/metric-definitions.md` (draft)
- `tests/contract/`

**Definition of Done / Gate**

- [ ] All valid sample records pass; all intentionally invalid records fail with useful messages.
- [ ] A new adapter author could understand GRDC from documentation and test fixtures alone.
- [ ] External IDs, currencies, timestamps, nulls, and refund semantics are unambiguous.
- [ ] No original source field is silently discarded without being mapped, preserved as metadata, or documented as intentionally omitted.

---

## M2 — Toast & Squarespace adapters (Weeks 3–4 · 20 points)

**Goal:** Reliably convert **two different published vendor formats** into the same GRDC entities.

### Week 3: Toast

- [ ] Fabricate small Toast-style `OrderDetails.csv`, `ItemSelectionDetails.csv`, and `PaymentDetails.csv` fixtures using the **published column definitions**.
- [ ] Create a Toast importer that accepts required files and documents optional files.
- [ ] Identify records by scoped order/item/payment identifiers, not by row number alone.
- [ ] Normalize each table separately before joining; handle multiple items and multiple payments.
- [ ] Validate required column presence by **header name**, even when order changes.
- [ ] Handle time zones and restaurant business days.
- [ ] Report missing source relationships and orphaned rows instead of silently dropping them.
- [ ] Write import run metadata: file hash, adapter version, row totals, accepted/rejected counts.

### Week 4: Squarespace Commerce

- [ ] Fabricate a realistic **multiline** order export based on published columns.
- [ ] Parse one source order spanning multiple CSV rows into exactly one order and N item records.
- [ ] Restore order-level context for continuation rows **without** incorrectly carrying one order's fields into the next.
- [ ] Preserve unknown/unsupported payment and restaurant fields as missing.
- [ ] Re-import an order with an updated financial status or refund and update canonical state safely.
- [ ] Maintain source snapshots/lineage to explain when and why a value changed.

### Shared adapter and ingestion tasks

- [ ] Define one adapter interface: source inspection, capability report, parsing, validation, canonical output, errors.
- [ ] Keep adapter logic in `backend/app/adapters/`; keep analytics unaware of vendor names.
- [ ] Write accepted rows into canonical PostgreSQL tables; quarantine rejected rows with reason codes.
- [ ] Re-import identical file twice and verify **no change** in canonical counts/financial totals.
- [ ] Fail safely on missing mandatory files/columns, inconsistent currency, or broken references.
- [ ] Write financial reconciliation tests for source orders → canonical orders → items/payments/refunds (where source provides them).
- [ ] Add a deterministic local import command and usage instructions to `README.md`.

**Files to submit**

- `backend/app/adapters/toast/`, `backend/app/adapters/squarespace/`
- `backend/app/ingestion/`, `backend/migrations/`
- `tests/fixtures/toast/`, `tests/fixtures/squarespace/`
- `tests/integration/`, `docs/adapter-compatibility.md`

**Definition of Done / Gate**

- [ ] **Toast test:** 1 order + 3 items + 2 payments remains **1 / 3 / 2** (not 6 orders).
- [ ] **Squarespace test:** 1 multiline order + 3 items becomes **1 / 3** without losing fields.
- [ ] Same logically equivalent mock order from either adapter yields equivalent canonical metrics (where fields overlap).
- [ ] Repeated identical imports are idempotent; an updated refund/order is reflected exactly once.
- [ ] Zero silent drops; rejected rows and field limitations appear in an import report.

---

## M3 — Multi-location SQL analytics (Week 5 · 15 points)

**Goal:** Make restaurant operators trust the **same metric definitions** regardless of where an order originated.

### Tasks

- [ ] Generate a **seeded** 10-location restaurant dataset, including POS orders, online orders, menu items, partial refunds, discounts, and variable-cost assumptions.
- [ ] Add organization and location keys to all operational records.
- [ ] Define `gross_sales`, `net_sales`, `refunds`, `recognized_sales`, `visits`, and `repeat_purchase_rate` in `docs/metric-definitions.md`.
- [ ] Define what a “visit” means when a source lacks guest identifiers or when one guest places multiple orders.
- [ ] Define and implement contribution margin using documented variable costs; if costs are absent show **not available**.
- [ ] Write reusable SQL queries/views by location, business day, channel, customer segment, and campaign.
- [ ] Compute customer match coverage and distinguish anonymous customers from known customers.
- [ ] Test two one-to-many joins to ensure order amounts are never multiplied.
- [ ] Reconcile location/day metrics against independently computed reference totals on fixtures.
- [ ] Document limitations of cross-location comparison (traffic, store size, menu, geography, sample size).

**Files to submit**

- `scripts/generate_demo_data.py` (or equivalent)
- `sql/` metric definitions and views
- `docs/metric-definitions.md`
- `tests/unit/` and `tests/integration/` for metrics

**Definition of Done / Gate**

- [ ] Exact-match fixture totals agree to the cent; no unexplained discrepancy.
- [ ] Repeat imports and source changes do not distort reports.
- [ ] The same SQL metric logic works for both adapter outputs.
- [ ] Missing customer or COGS fields are visible as coverage gaps, not silently imputed.

---

## M4 — Incrementality & campaign economics (Week 6 · 15 points)

**Goal:** Distinguish *observed/attributed revenue* from **causally estimated incremental outcomes**.

### Tasks

- [ ] Define treatment, control, assignment unit, assignment timestamp, analysis window, outcome, and exclusion rules.
- [ ] Use **Hillstrom** to reproduce treatment/control outcome differences on a real randomized non-restaurant dataset.
- [ ] Verify covariate balance and examine randomization/selection limitations.
- [ ] Implement intent-to-treat effect estimation for conversion and revenue per assigned customer.
- [ ] Compute uncertainty intervals and sample sizes; label statistically inconclusive results.
- [ ] Build a **separate seeded fictional restaurant experiment** with known assignment and outcome-generating rules.
- [ ] Add a transparent profit scenario: incremental net contribution from purchases minus eligible incentive/communication costs, without double counting discounts.
- [ ] Test sensitivity to product margin and campaign cost assumptions.
- [ ] Make the engine refuse a causal claim when no valid randomized assignment or defensible identification strategy exists.
- [ ] Prevent post-treatment leakage in any segmentation/modeling pipeline.
- [ ] Compare findings with a simple baseline before attempting optional uplift ML.
- [ ] Document what is *measured*, what is *estimated*, and what is *assumed*.

**Files to submit**

- `backend/app/analytics/experiments/`
- `docs/experiment-methodology.md`
- Reproducible Hillstrom analysis notebook or script
- Unit tests with known synthetic treatment effects

**Definition of Done / Gate**

- [ ] Hillstrom results can be reproduced from downloaded raw data.
- [ ] Synthetic test estimators recover expected patterns within documented sampling uncertainty.
- [ ] The product never labels observational offer redemptions “incremental profit.”
- [ ] An experiment without sufficient evidence returns **inconclusive / insufficient data**.

---

## M5 — Website & operator workflow (Week 7 · 10 points)

**Goal:** Build a polished, truthful application that a restaurant marketing lead can use without reading Python or SQL.

### Required pages

- [ ] `/` — Marketing homepage, product value, honest demo caveats, clear “Explore Demo” link.
- [ ] `/demo` — Preloaded fictional multi-location chain and campaigns; no signup required.
- [ ] `/data-sources` — Toast/Squarespace supported formats and required/missing fields.
- [ ] `/imports` — Choose provider, upload fake CSV fixture, see validation results, rejection details, and audit history.
- [ ] `/campaigns` — Attributed results **versus** incremental estimate (only when supported), margin assumptions, sample size, uncertainty.
- [ ] `/locations` — Operational comparisons with drill-down and coverage indicators.
- [ ] `/standard` — GRDC field documentation, schema downloads, example records, compatibility policy.
- [ ] `/methodology` — Metric definitions, statistical limitations, generated-data disclosure.

### Backend/frontend tasks

- [ ] Create typed FastAPI endpoints for import jobs, canonical records, operational metrics, and campaign analysis.
- [ ] Connect Next.js frontend to the API; no hardcoded dashboard totals presented as live computed outputs.
- [ ] Add empty, invalid, loading, failed-import, and inconclusive-result states.
- [ ] Build a demonstration flow: upload Toast fixture → inspect canonical records → show reconciled financial totals → inspect campaign report.
- [ ] Repeat the flow with Squarespace fixture and show the **same GRDC-backed analysis**.
- [ ] Ensure synthetic numbers and fictional brand names are visibly labeled.
- [ ] Add documentation and a concise demo script showing what a pilot customer would learn.

**Files to submit**

- `frontend/`, `backend/app/api/`, `docs/demo-script.md`
- Updated root `README.md` with screenshots / quickstart once working

**Definition of Done / Gate**

- [ ] A new reviewer can run the app using documented local steps.
- [ ] Reviewer can trace a displayed metric back to the input fixture, canonical record, and calculation.
- [ ] UI displays negative, zero, missing, and inconclusive outcomes correctly.
- [ ] Landing page includes **no invented real customer testimonials, contracts, or ROI claims**.

---

## M6 — Reliability, scale & pilot-readiness (Week 8 · 10 points)

**Goal:** Demonstrate that GuestLift is a dependable, repeatable software product foundation—not only a scripted demo.

### Reliability and performance tasks

- [ ] Run automated unit, contract, integration, and metric tests on every pull request using GitHub Actions.
- [ ] Test missing files/columns, malformed amounts, bad encoding, duplicate rows, and partial uploads.
- [ ] Test replay after interrupted import and verify no duplicated transactions.
- [ ] Test updated payment/refund state, corrected order, and source schema column reordering.
- [ ] Test organization isolation: tenant A cannot read or aggregate tenant B's data.
- [ ] Test time zones and orders near midnight / business-day rollover.
- [ ] Generate and process **100,000** test orders, then **1,000,000** test orders; record runtime, memory, and DB query costs.
- [ ] Benchmark time to onboard a third **mock provider** using only GRDC docs and adapter interface (do not implement third full provider unless time allows).
- [ ] Record known security gaps preventing production use with real personal data.
- [ ] Verify clean local setup from a fresh clone and document every dependency.

### Final review and pilot preparation

- [ ] Create `docs/benchmarks.md` with machine specs, dataset generator seed, measurements, bottlenecks, and next optimizations.
- [ ] Create `docs/security-and-privacy.md` covering least-privilege access, PII minimization, retention, auditing, and missing production controls.
- [ ] Create a 5–8 minute reproducible end-to-end technical demo.
- [ ] Create `docs/pilot-plan.md` for an authorized 5–30-location restaurant group: input files, required cost data, assignment logs, sample-size feasibility, success metrics, and privacy approvals.
- [ ] Perform a final technical defense: explain the data model, normalization, idempotency, financial logic, statistical assumptions, and limitations.
- [ ] Publish a technical case study with screenshots, tests, benchmarks, and clearly labeled sample results.

**Definition of Done / Gate**

- [ ] CI passes from a clean checkout; critical regression tests pass.
- [ ] Reimports, failures, and refunds cannot quietly corrupt financial totals.
- [ ] Scaling benchmarks are reproducible and measured (no unsupported “enterprise-scale” claim).
- [ ] The public demo uses only approved/public/synthetic information.
- [ ] A restaurant operator could understand what input data a pilot requires and what decision the analysis would support.

---

## 6. Cross-milestone acceptance test suite

Use this as the permanent conformance checklist. Tests start as fixtures during M1/M2 and remain in CI afterward.

- [ ] **One-to-many:** 1 order, 3 items, 2 payments stays 1 / 3 / 2 (no 6× inflation).
- [ ] **Squarespace continuation rows:** 3 line items produce one order with correct header totals.
- [ ] **Refund update:** changed refund status changes recognized sales once, with lineage.
- [ ] **Import replay:** importing identical content twice changes no accepted totals.
- [ ] **Column drift:** reordered CSV columns work; missing required columns produce actionable errors.
- [ ] **Business date:** UTC and location-local order date are both preserved correctly.
- [ ] **Unknown customer:** anonymous order is valid; customer analytics indicate incomplete identity coverage.
- [ ] **Unknown costs:** no COGS → no invented contribution margin.
- [ ] **Zero versus null:** explicit $0 discount differs from unavailable discount data.
- [ ] **Mixed currencies:** do not sum USD and EUR without explicit conversion logic (out of scope).
- [ ] **Causal validity:** no control/valid design → no causal incremental-lift claim.
- [ ] **Tenant isolation:** records never cross organizations in queries or APIs.
- [ ] **Contract versioning:** an additive optional field preserves valid old fixtures.
- [ ] **Provenance:** every output links to an import run, adapter version, source, and formula version.

---

## 7. GitHub Issues & project management

Suggested labels: `milestone:M0` through `milestone:M6`, `area:data-contract`, `area:adapter`, `area:database`, `area:analytics`, `area:frontend`, `area:testing`, `type:research`, `type:bug`, `blocked`.

**Issue template:**

```markdown
### Objective
What outcome does this task support?

### Requirements
- [ ] Requirement 1
- [ ] Requirement 2

### Acceptance test
Describe exactly how to prove completion (expected input/output).

### Evidence
Link to PR, tests, query output, screenshot, or report.

### Dependencies / blockers
Link to related issues.
```

**Working habits**

- [ ] One issue/branch per independently reviewable feature.
- [ ] Commit tests and implementation together when practical.
- [ ] Attach evidence to a pull request and review against the milestone gate.
- [ ] Record architectural choices in `docs/decisions/` with: context, alternatives, decision, tradeoffs.
- [ ] Revisit scope every milestone; move nice-to-have features to **Later** instead of expanding v1 indefinitely.

---

## 8. Restaurant discovery and commercial path (parallel track)

**These activities improve future commercial viability but do not replace engineering tasks.**

### During development

- [ ] Identify 10 fast-casual restaurant groups with 5–50 locations and a recurring promotion/loyalty program.
- [ ] Speak with 5 operators/CRM/marketing leaders: how they evaluate promotions, which exports they use, and what existing tools cannot tell them.
- [ ] Ask whether they can run randomized holdouts and provide product-level costs; do not ask for customer data initially.
- [ ] Update the proposed business question if interviews reveal a more painful decision.
- [ ] Demonstrate the working synthetic GuestLift app and note specific requests/objections.

### Before a real pilot

- [ ] Obtain written authorization and appropriate agreements for any merchant data.
- [ ] Minimize/mask personal data; never ingest card numbers or payment credentials.
- [ ] Implement production-appropriate access controls, encryption, backups, monitoring, privacy practices, and tenant isolation before real data use.
- [ ] Assess available campaign assignments, guest matching, cost data, and sample size.
- [ ] Define one realistic decision to evaluate, baseline, time window, and uncertainty reporting.
- [ ] Do not promise causal results when experimental identification is not possible.

**Potential business model to test:** fee for an initial promotional-profitability analysis, then recurring measurement software if merchants repeatedly need the same workflow. **Unvalidated until customers agree to pay.**

**Long-term optional expansion:** Square POS, Shopify, Clover, loyalty systems, experience-based rewards, merchant-funded offers, and issuer/Amex/Chase partnerships. None are requirements for v1.

---

## 9. Overall definition of done

### Capstone complete when

- [ ] GRDC v0.1.0 is published with schemas, examples, version policy, and conformance tests.
- [ ] Toast and Squarespace **published-format** adapters pass their fixture and reconciliation suites.
- [ ] A multi-location relational model produces exact, documented SQL metrics.
- [ ] A randomized-marketing analysis is reproducible and clearly distinguished from synthetic restaurant results.
- [ ] The web demo is interactive, truthful, and traceable to backend calculations.
- [ ] Import reruns, updates, failures, and tenant isolation are tested.
- [ ] Scaling results and setup steps are documented.
- [ ] You can explain and defend the core engineering and statistical decisions independently.

### Product validated only when

- [ ] At least one operator describes a specific important decision current tools do not answer well.
- [ ] A merchant can actually supply the required authorized data.
- [ ] A valid, sufficiently powered evaluation supports a credible decision.
- [ ] The merchant finds the result useful enough to act on and potentially pay for.

---

## 10. START HERE — First work session (in exact order)

**No frontend coding yet.** The first task is to establish the project contract and verify the inputs.

1. [ ] Create repository `guestlift` and commit this `ROADMAP.md` at its root.
2. [ ] Create `README.md` with a one-paragraph product pitch and an explicit **prototype / simulated-data** disclaimer.
3. [ ] Create `docs/proposal.md` with the exact business question and the fictional 10-location campaign scenario.
4. [ ] Open the [Toast field reference](https://doc.toasttab.com/doc/platformguide/adminDataExportFieldReference.html); list file names, grains, IDs, amounts, timestamps, and fields unavailable for analysis.
5. [ ] Open the [Squarespace CSV guide](https://support.squarespace.com/hc/en-us/articles/206540677-Export-Commerce-orders); list order and line-item fields and note multiline and update behavior.
6. [ ] Create `docs/source-inventory.md` and record the two vendor capabilities side by side.
7. [ ] List **10 failure cases** we must test (missing item, duplicate payment, partial refund, absent customer, etc.).
8. [ ] Sketch the initial GRDC `orders` and `order_items` entities; mark each field required, optional, or unknown.
9. [ ] Commit the proposal and inventory; use them to review M0 before M1 implementation.

**First checkpoint question:** *Can we transform one Toast order and one Squarespace order into the same defined business representation without silently losing or inventing information?*

---

## 11. Reference links

- Toast: [Data Export Field Reference](https://doc.toasttab.com/doc/platformguide/adminDataExportFieldReference.html) · [Export Overview](https://doc.toasttab.com/doc/platformguide/adminDataExportOverview.html)
- Squarespace Commerce: [Order Exports](https://support.squarespace.com/hc/en-us/articles/206540677-Export-Commerce-orders) · [Commerce APIs](https://developers.squarespace.com/commerce-apis/overview)
- Public learning data: [Maven Cafe Rewards](https://mavenanalytics.io/data-playground/cafe-rewards-offers) · [Hillstrom Experiment](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html)
- Technical references: [FastAPI](https://fastapi.tiangolo.com/) · [PostgreSQL](https://www.postgresql.org/docs/) · [JSON Schema](https://json-schema.org/learn/getting-started-step-by-step) · [Next.js](https://nextjs.org/docs) · [pytest](https://docs.pytest.org/)

> **Operating principle:** Build *a correct, traceable, vendor-neutral data foundation* first. Add sophisticated analysis and UI only after the data contract and financial controls work. A “not enough evidence” answer is better than a confident but incorrect recommendation.
