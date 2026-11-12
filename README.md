# GuestLift

**One data standard. Multiple restaurant POS systems. Consistent analytics.**

GuestLift is an independent, demo-first data engineering project exploring how restaurants can bring transaction information from different POS platforms into a reliable, vendor-neutral analytics system.

## The problem

Toast POS and Square POS represent restaurant orders and payments differently. Restaurants operating across systems need a dependable way to validate, standardize, and compare their data before using it for business decisions.

**The first product demonstration:** Select a Toast or Square test source, watch an order move through a data pipeline, inspect its canonical GuestLift representation, and view the same sales metrics computed by one analytics layer.

## How it works

**Toast CSVs / Square Sandbox orders → Provider adapters → GuestLift Restaurant Data Contract (GRDC) → PostgreSQL → Shared SQL analytics → FastAPI → Next.js website.**

See the **[visual architecture and five-minute demo storyboard](docs/architecture.md)**.

## Roadmap

Follow the **[demo-first development checklist](ROADMAP.md)**. We are starting with a clear website/architecture demonstration, then implementing the two adapters and replacing mocked screens with verified pipeline outputs.

Read the short [BU-style project proposal](docs/proposal.md).

## Planned technology

| Component | Stack |
|---|---|
| Source ingestion | Python, Pandas, Pydantic |
| Canonical records and reporting | GRDC, PostgreSQL, SQL, SQLAlchemy |
| API | FastAPI |
| Website | Next.js, TypeScript, Tailwind CSS |
| Tests and local development | pytest, GitHub Actions, Docker Compose |

## Data and current status

The initial Toast files will be **fabricated fixtures based on vendor documentation**; Square test data will come from **Square Sandbox**. We are not connected to live restaurant accounts. Early website views may be labeled mockups until connected to actual local pipelines.

This project does **not** claim verified restaurant ROI, production-ready integrations, or payment-card access. GRDC is a **proposed project data contract**, not a broadly adopted industry standard.

## Longer-term goal

Once the underlying data pipeline is dependable, GuestLift can expand toward multi-location loyalty and campaign analytics, and eventually test incremental-profit measurement with authorized merchant data and appropriate experiment designs.
