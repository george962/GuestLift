# GuestLift — Project Proposal

**Project:** Independent Data Engineering Capstone  
**Milestone:** M0 — Proposal and Source Feasibility  
**Version:** 0.1 (Draft)  
**Date:** November 12, 2026  
**Repository:** [GuestLift](https://github.com/george962/GuestLift) · [Roadmap](../ROADMAP.md)

## 1. Problem Statement

Fast-casual restaurant chains regularly use discounts, loyalty points, free menu items, and other promotional offers to encourage repeat visits. However, revenue attributed to a promotion is not necessarily *incremental*: some customers would have purchased even without the offer. Promotions can also increase sales while reducing profit once discounts, food costs, refunds, and fulfillment expenses are considered.

For multi-location restaurant groups, this problem is complicated by fragmented data. Restaurant POS, online commerce, and marketing systems record orders, payments, line items, customers, and campaigns in different formats. Inconsistent definitions and data quality can produce misleading comparisons between locations and campaigns.

**Primary business question:** *Which loyalty and promotional campaigns generate incremental contribution profit, and how should a multi-location restaurant group use that information to improve future marketing decisions?*

GuestLift will explore this question by designing a vendor-neutral data standard and an analytics application that transforms provider-specific records into consistent, traceable metrics. The initial target users are marketing, loyalty, operations, and finance teams at fast-casual groups with approximately **5–50 locations**.

## 2. Objectives

1. **Define a common data standard.** Design a versioned *GuestLift Restaurant Data Contract* (GRDC) describing locations, orders, order items, payments, refunds, customers, campaigns, and experiment assignments.
2. **Build interoperable data adapters.** Convert test exports based on published **Toast POS** and **Squarespace Commerce** formats into the same canonical records.
3. **Deliver reliable business analytics.** Calculate sales, customer frequency, promotion activity, and contribution metrics in PostgreSQL while reconciling financial totals and flagging incomplete data.
4. **Measure promotional impact responsibly.** Distinguish campaign-attributed sales from causal incremental effects using valid treatment/control comparisons, uncertainty estimates, and transparent cost assumptions.
5. **Create a working demonstration.** Build a web application that lets a reviewer inspect imports, evaluate a fictional campaign, compare locations, and trace reported metrics to source data.

The initial product will **not** process payments, issue actual rewards, integrate with banks, or claim that GRDC is an adopted industry standard.

## 3. Initial Business Scenario

The demonstration will feature a **fictional fast-casual chain with 10 locations**. Its director of loyalty marketing wants to evaluate whether a weekday lunch offer—**a free side item with a qualifying purchase**—should be repeated or expanded.

A seeded, synthetic experiment will assign eligible customers to either an offer-invitation group or a control group *before* measuring subsequent purchases. The system will report outcomes over a specified observation window and show how economic assumptions affect the result.

Three core outcomes will be defined in advance:

- **Incremental visits:** The estimated difference in visits caused by the offer compared with what would have occurred without it.
- **Incremental revenue:** The estimated difference in net purchase revenue between the assigned groups.
- **Incremental contribution profit:** The estimated difference in net sales less relevant variable operating, fulfillment, and campaign costs, avoiding double-counted discounts.

Customer reward redemptions alone do **not** establish incrementality. If randomized assignments, sufficient sample sizes, or cost inputs are unavailable, GuestLift must show descriptive results, missing-data warnings, or an inconclusive assessment rather than an unsupported profit-lift claim.

## 4. Data Sources

| Source | Acquisition | Intended use | Important limitations |
|---|---|---|---|
| **Toast export documentation** | [Official field reference](https://doc.toasttab.com/doc/platformguide/adminDataExportFieldReference.html) | Define sample order, item-selection, and payment CSV formats; develop Toast adapter | Documentation is **not** actual merchant transaction data; exported fields may vary |
| **Squarespace Commerce documentation** | [Official order export guide](https://support.squarespace.com/hc/en-us/articles/206540677-Export-Commerce-orders) | Define multiline commerce-order CSV test inputs; develop Squarespace adapter | Commerce orders are not equivalent to complete restaurant POS records; exports may not capture subsequent changes automatically |
| **Cafe Rewards Offers** | [Maven Analytics Data Playground](https://mavenanalytics.io/data-playground/cafe-rewards-offers) | Explore offer-received, offer-viewed, offer-completed, and purchase event ingestion | Simulated marketing data, not a real restaurant causal experiment |
| **Hillstrom email experiment** | [MineThatData](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html) | Validate the randomized treatment/control analysis methodology | Historic **apparel retail**, not restaurant data; lacks restaurant contribution costs |
| **Seeded multi-location simulator** | Developed as part of GuestLift | Generate fictional transactions, campaign assignments, costs, refunds, and error cases for testing | Synthetic data proves software behavior, not actual commercial impact |
| **Potential merchant-authorized exports** | Future voluntary restaurant pilot | Assess performance with real transactions and marketing records | Not available at launch; requires permission, privacy safeguards, and sufficient data |

**Data verification remains part of Milestone M0.** Dataset download terms, actual file columns, row counts, and relevant field gaps will be recorded after inspecting the files. The initial Toast and Squarespace imports will use fabricated fixtures shaped according to published vendor formats.

## 5. Methodology

### 5.1 Data ingestion and normalization

Document each source file's grain, identifiers, and available fields. Design GRDC schemas with explicit definitions for order, item, payment, refund, and campaign records. Implement Python adapters that parse the two vendor formats, map fields, retain provenance, and validate canonical output before loading it into PostgreSQL.

### 5.2 Data quality and financial reconciliation

Create repeatable tests for missing identifiers, duplicate imports, repeated line items, partial refunds, status updates, and mismatched totals. Keep order-, line-item-, and payment-level relationships separate so one-to-many joins cannot accidentally multiply revenue. Monetary calculations will use integer minor currency units; missing values will not be treated as zero.

### 5.3 Restaurant analytics

Use SQL to calculate net sales, order and customer frequency, campaign participation, location-level performance, and estimated contribution margin. Report data coverage and missing cost information. Comparisons among locations will be descriptive unless a valid experiment or another defensible causal design supports stronger claims.

### 5.4 Incrementality analysis

Use the randomized Hillstrom dataset to validate the statistical estimation procedure independently of the fictional restaurant data. Build a separate reproducible synthetic restaurant experiment with known assignment rules. Estimate intention-to-treat effects, report uncertainty intervals, and distinguish observed, estimated, and assumed quantities. Analyze the sensitivity of profit estimates to unit economics and campaign costs.

### 5.5 Web application and reproducibility

Expose validated metrics via **FastAPI** and create a **Next.js** interface showing source imports, data quality, campaign outcomes, and location comparisons. Use Docker Compose for local reproducibility, pytest for automated checks, and GitHub Actions for continuous integration. Every displayed demo result should be traceable to an input, transformation, and documented metric definition.

## 6. Tools and Environment

| Layer | Planned technologies |
|---|---|
| Development and version control | VS Code, Git, GitHub |
| Data ingestion and validation | Python, Pandas, Pydantic, JSON Schema |
| Database and data models | PostgreSQL, SQL, SQLAlchemy, Alembic |
| Statistical analysis | NumPy, SciPy, statsmodels |
| Backend | FastAPI |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Testing and local execution | pytest, GitHub Actions, Docker Compose |

Development will begin locally with a target of **$0 in required cloud infrastructure**. Cloud hosting, automated vendor API access, streaming, and advanced ML are out of the initial scope unless a later milestone demonstrates a concrete need.

## 7. Expected Outcomes

At completion, the capstone should provide:

1. A documented, versioned GRDC specification and two working CSV provider adapters.
2. A PostgreSQL analytical model that produces reconciled, provider-neutral metrics.
3. A reproducible fictional 10-location campaign scenario with explicit financial assumptions.
4. An experiment module that reports uncertainty and refuses unsupported causal conclusions.
5. A functional web demonstration showing campaign and location results, import checks, and calculation methodology.
6. Automated reliability tests, a local setup guide, and a narrowly scoped proposal for a possible restaurant pilot.

**Success criteria:** Correct financial totals, idempotent imports, visible data limitations, reproducible results, and a demonstration understandable to a nontechnical restaurant operator. Specific milestone gates are maintained in [ROADMAP.md](../ROADMAP.md).

## 8. Constraints and Risks

- **No initial production data:** Published vendor schemas do not grant access to real restaurant transactions. Pilot data must be authorized by an operator.
- **Incomplete economic data:** Variable food costs, fees, campaign expenses, and marketing assignment logs may be absent from standard exports and require additional sources.
- **Limited causal evidence:** Simulated rewards events cannot establish real restaurant incrementality; the Hillstrom experiment validates methodology only in another industry.
- **Differences between platforms:** Toast POS and Squarespace Commerce support different workflows. Some fields may be unmappable and must remain explicitly unknown.
- **Customer privacy and security:** The prototype will use public/synthetic inputs only. Real customer analysis would require appropriate agreements, consent or other lawful basis, access controls, security review, and data retention policies.
- **Commercial uncertainty:** A reliable prototype does not establish that restaurants need or will pay for another analytics provider. Operator discovery and an actual pilot are separate validation steps.

## 9. Proposed Timeline

| Target week | Milestone | Main deliverable |
|---|---|---|
| 1 | **M0** — Proposal and source feasibility | Business case and verified source inventory |
| 2 | **M1** — GRDC data standard | Schemas, documentation, contract tests |
| 3–4 | **M2** — Toast and Squarespace adapters | Repeatable importers and reconciliation tests |
| 5 | **M3** — Multi-location analytics | SQL metrics and fictional chain data |
| 6 | **M4** — Campaign incrementality | Experiment engine and economics |
| 7 | **M5** — Website and workflow | Functional operator-facing demo |
| 8 | **M6** — Reliability and pilot readiness | Tests, benchmarks, documentation, pilot proposal |

**Current status:** Proposal drafted; data-source inspection and the rest of Milestone M0 have not yet been completed.
