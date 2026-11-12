# GuestLift — BU-Style Project Proposal

**Project:** GuestLift — Vendor-Neutral Restaurant Analytics  
**Version:** 0.2, revised for a demo-first capstone (November 12, 2026)  
**Roadmap:** [ROADMAP.md](../ROADMAP.md) · **Architecture:** [architecture.md](architecture.md)

## 1. Problem Statement

Restaurants that use different point-of-sale systems often receive sales, order, and payment information in different formats. Even when the information represents similar business activity, combining it can require custom transformations and reconciliation. This makes it harder for a multi-location restaurant operator to develop consistent reports or extend its analysis to customer behavior and loyalty programs.

GuestLift asks: **Can we build a reusable, vendor-neutral ingestion and analytics platform that converts Toast POS and Square POS data into one reliable model and makes the results understandable to restaurant operators?**

The longer-term business goal is better promotion and loyalty profitability analysis, but the initial capstone focuses on demonstrating trustworthy data interoperability.

## 2. Objectives

1. **Show the product clearly.** Build a professional website explaining the problem and illustrating the end-to-end data pipeline.
2. **Standardize vendor data.** Propose a GuestLift Restaurant Data Contract (GRDC) for orders, items, payments, and locations.
3. **Support two distinct sources.** Convert Toast-style CSV files and Square API-shaped synthetic fixtures into the same GRDC entities.
4. **Verify the results.** Detect malformed and duplicate records, preserve data lineage, and reconcile financial metrics.
5. **Provide actionable reporting foundations.** Display consistent restaurant-level order and sales metrics using one SQL analytics layer.

## 3. Data Sources

**Toast POS:** Publicly documented [data export formats](https://doc.toasttab.com/doc/platformguide/adminDataExportFieldReference.html). First-version imports will use synthetic files shaped after the published order, item, and payment exports. No private merchant data is assumed.

**Square POS:** [Square Orders API](https://developer.squareup.com/reference/square/orders) and [free Sandbox](https://developer.squareup.com/docs/devtools/sandbox/overview) to generate and retrieve test orders. Square POS is a distinct product from Squarespace Commerce.

**Additional data:** Small, generated test cases used to exercise duplicate imports, missing fields, refunds, and multi-item orders. Real restaurant campaign assignments and costs are a future pilot requirement, not something this demonstration invents.

## 4. Methodology

**Phase A — Product story and visual design.** Create an architectural diagram and an interactive website prototype. A visitor will select Toast or Square and follow a sample order from the source format through ingestion and standardization to shared reporting.

**Phase B — Source adapters.** Implement Python parsers for Toast sample CSVs and Square API-shaped synthetic JSON. Each adapter maps provider data into GRDC and explains missing or unsupported fields.

**Phase C — Canonical data and analysis.** Validate records using Pydantic or JSON Schema, store them in PostgreSQL, and calculate order counts, sales, and discount/refund metrics using shared SQL queries. Include audit records and tests to prevent double counting.

**Phase D — Connected application.** Serve imports and analytics through FastAPI and connect a Next.js frontend. Replace initial mock outputs with actual computed values; document how every demo number is derived.

**Phase E — Reliability and presentation.** Run automated tests, package local services with Docker Compose, and prepare a five-minute demonstration for potential restaurant operators or technical reviewers.

## 5. Technology Stack

Python, Pandas, Pydantic, PostgreSQL, SQL, SQLAlchemy/Alembic, FastAPI, Next.js, TypeScript, Tailwind CSS, pytest, GitHub Actions, and Docker Compose. Development begins locally; no paid cloud infrastructure is required for the capstone.

## 6. Expected Outcomes

- A publicly understandable product explanation and architecture diagram.
- An interactive website demo with Toast and Square source examples.
- Two working provider adapters that produce the same canonical records.
- Reproducible reporting with explicit validation and source traceability.
- A documented technical foundation for future loyalty and promotional-profitability analysis.

The main evaluation criterion is whether another person can understand, run, and verify the end-to-end demonstration—not the number of dashboards or models added.

## 7. Constraints and Risks

- Public documentation does **not** grant access to a restaurant's actual Toast or Square transaction history. Production integrations require authorization and permissions.
- Square Sandbox test orders and fabricated Toast CSVs are **not evidence** of real merchant outcomes.
- The platforms have different fields and business semantics. Some information will remain unknown rather than being invented.
- The first demo does not establish causal incremental sales or actual contribution profit; such claims require suitable experiment and cost data.
- The prototype is not yet designed to handle live customer-sensitive data; a pilot would need security, privacy, and operational controls.

## 8. Work Plan

Follow the milestone gates in [ROADMAP.md](../ROADMAP.md): architecture → clickable demo → Toast adapter → Square adapter → database/reporting → connected demo → reliability and pilot-readiness.

## Implementation checkpoint (November 12, 2026)

The first downloadable prototype now includes a Next.js website and a FastAPI backend that normalizes fabricated Toast-style CSV records and Square API-shaped JSON records into a common order model. SQL persistence, sample metric endpoints and seven pytest checks are included. **There is no actual Square Sandbox connection yet**; formal frontend build/browser testing and external merchant integrations remain open items. See [Implementation Status](IMPLEMENTATION_STATUS.md).
