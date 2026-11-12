# GuestLift

**Vendor-neutral loyalty analytics and promotional profitability for multi-location restaurants.**

> **Status:** Planning — independent data engineering capstone (v2.1). The application and integrations have not been implemented yet.

## The problem

Restaurant groups can report sales attributed to a promotion without necessarily knowing whether it **caused additional visits or contribution profit**. Comparing results across locations and vendors is harder when order, payment, customer, and campaign data use different formats.

**GuestLift's core question:** *Which loyalty and promotional campaigns generate incremental contribution profit, and how should a restaurant group adjust future campaigns across locations?*

## Who it's for

Initially, fast-casual restaurant groups with approximately **5–50 locations**, especially their marketing/loyalty, CRM, operations, and finance teams.

## What we're building

A working demonstration in which a **fictional 10-location restaurant chain** can:

1. Import sample data shaped like **Toast POS** and **Squarespace Commerce** exports.
2. Normalize both providers' records into the proposed, versioned **GuestLift Restaurant Data Contract (GRDC)**.
3. Validate and reconcile orders, payments, discounts, refunds, and customer activity.
4. Explore campaign performance by location, with financial assumptions clearly identified.
5. Estimate incremental effects **only when valid experimental data supports the analysis**, and show uncertainty or insufficient-evidence warnings otherwise.

**Initial architecture:** Source adapters → GRDC validation → PostgreSQL → SQL analytics / experiment analysis → FastAPI → Next.js dashboard.

## Technology (planned)

| Layer | Tools |
|---|---|
| Data ingestion and validation | Python, Pandas, Pydantic, JSON Schema |
| Database and transformations | PostgreSQL, SQL, SQLAlchemy |
| Experiment analysis | Python, statsmodels, scikit-learn (as needed) |
| Backend API | FastAPI |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Testing and local development | pytest, GitHub Actions, Docker Compose |

Development starts **locally**, targeting **$0 in required cloud infrastructure**. The stack may change as requirements are validated.

## Data and evidence

- **Toast and Squarespace:** Official export/API documentation informs adapter schemas. Initial test files are **synthetic fixtures**, not actual merchant transactions.
- **Cafe Rewards Offers:** Publicly available **simulated** loyalty events for ingestion and analytical exercises.
- **Hillstrom email experiment:** Historical randomized **retail (not restaurant)** data for checking incrementality methods.
- **Generated restaurant data:** Seeded, multi-location scenarios for reconciliation, error handling, and scale tests.
- **Future merchant pilot:** Would require authorized data, privacy safeguards, cost information, and an appropriate experiment design.

This project **does not claim real restaurant ROI from simulated data**, does not handle payment-card numbers, and is not affiliated with Toast, Squarespace, or any card issuer. GRDC is a **proposed project specification**, not an adopted industry standard.

## Roadmap

Follow **[ROADMAP.md](ROADMAP.md)** for the eight-week milestone plan, task checklists, deliverables, and definitions of done.

| Milestone | Focus |
|---|---|
| M0 | Business proposal and source feasibility |
| M1 | Versioned GRDC data standard |
| M2 | Toast and Squarespace source adapters |
| M3 | Multi-location SQL analytics |
| M4 | Incrementality and campaign economics |
| M5 | Operator-facing website and dashboard |
| M6 | Reliability, performance, and pilot readiness |

**Current next step:** M0 — set up the repository, document sources, and validate project feasibility. Implementation begins only after the relevant milestone requirements are met.

## Longer-term direction

If validated with restaurant operators, GuestLift could expand to additional POS and loyalty providers, experiential benefits, and eventually merchant-funded or card-linked offers. Those are future possibilities, **not features included in the current scope**.
