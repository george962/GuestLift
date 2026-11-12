# Brand system — GuestLift v0.5

**Meaning of the symbol:** a restaurant ontology. Four connected circles represent business entities (locations, customers, orders, promotions), linked to one validated transaction at the center. This is an illustrative product mark, not a claim of official vendor integrations.

**Visual hierarchy:** deep ink #17313B for trust/navigation; teal #087F73 for validated analytical metrics and actions; warm amber #AA713C for offer economics and assumptions; soft lavender #6C68A9 for analyst / customer intelligence; off-white #F6F8F6 for the working canvas. Never rely on color alone to communicate status.

**Information hierarchy:** 1) operator decision, 2) verified calculated evidence, 3) limitation and next action, 4) optional traceability and raw records.

**Navigation:** Public: Why GuestLift / Product / Pricing. Product workspace: Overview, Customers, Campaigns, Ask GuestLift, Data Sources, Account & Billing. Legacy technical pages remain accessible but are not promoted in the main navigation.

**Claims policy:** Always label synthetic data, modeled contribution vs measured discounts, deterministic rules vs actual LLM responses, and test billing vs live subscriptions.

---

## Archived v0.2 brand notes

# GuestLift Brand and Product Design System (v0.2)

## Audience and positioning

**Who:** Independent restaurant owners, marketing leads and multi-location operators; secondary: technical/data teams evaluating correctness.

**Message:** "Turn restaurant orders into decisions you can explain." The product connects disparate POS formats, verifies the shared record, and supports clearer financial choices about discounts and customer loyalty.

**Voice:** Direct, specific, calm and respectful. Explain a business outcome before describing the technology. Avoid buzzwords like "AI-powered growth" or unverifiable claims of revenue lift.

## Semantic design palette

| Role | Color | Hex | Where used |
|---|---|---|---|
| Foundation and trust | Deep navy | `#17313B` | Logo, headers, primary actions, major headings |
| Third-party input | Indigo | `#5368A8` | Toast/Square sample inputs and pre-normalized/source state |
| Normalized and validated | Teal | `#0C827B` | GRDC, passed checks, traceable metrics |
| Campaign decisions and estimates | Amber | `#A36C21` | Offer configuration, scenario modeling, uncertainty alerts |
| Cost, risk, investigation | Muted rose | `#AF5D59` | Financial tradeoffs, error and risk states |
| Background and separation | Cool off-white | `#F6F8F8` | Low-visual-noise application canvas |

Colors **never convey meaning alone**. Status messages also have text labels, numbers, and icons. Colors do not mean that a vendor is actually integrated or that a result is statistically significant.

## Information hierarchy

1. **Business decision** — The visible question: how much might this offer cost, and what information is still missing?
2. **Evidence** — Source order counts, dollars, financial assumptions, and missing inputs.
3. **Mechanism** — Provider-specific adapters, GRDC mapping, SQL analytics and source lineage.

## Website information architecture

| URL | Primary purpose | Visitor action |
|---|---|---|
| `/` | Product positioning for an operator | Open offer studio |
| `/offers` | Adjust coupon inputs and explore a financial scenario | Change inputs; inspect eligible sample orders |
| `/demo` | Observe data provenance and normalization | Run sample Toast or Square import |
| `/how-it-works` | Explain adapter and GRDC architecture | Understand data processing |

## Trust and privacy conventions

- Badge public sample data clearly and repeatedly.
- Public prototype does not accept real merchant files, payment information, or customer identifiers.
- No invented testimonials, integrations, claimed loyalty lift, or customer logos.
- Report "unknown" when a metric requires data not present.
- A coupon code in the offer studio is **only a scenario label**; it is not a measured coupon redemption.
- Break-even added orders are a **scenario threshold** under assumptions, not a traffic forecast.

## Visual implementation

The design tokens are defined in `frontend/app/globals.css`. Components in the new public homepage and offer studio use `gl-` classes. This reduces conflict with the initial pipeline demo CSS during the transition. A future cleanup can migrate legacy demo classes to shared tokens without changing the underlying calculations.

## v0.3 identity improvement — the two-to-one mark

The new GuestLift logomark is an **original SVG** defined in `frontend/components/brand-mark.tsx`. Two indigo paths enter from the left and converge on a teal, validated record before one output travels to the right. This is meaningful: **different POS formats → one verified business model**. It avoids a generic growth chart icon that could represent any analytics product.

Use the palette operationally: indigo means provider data, teal means data passed through the GRDC parser, amber means hypothetical coupons/assumptions, rose means failures/financial risks, and navy means application structure. The brand mark uses only the source/validated colors, because neither campaign estimates nor warnings are the brand's core identity.

The homepage hero now contains a **working selectable order walkthrough** in place of a simulated screenshot. The Import Lab uses visible validation, file selection, live totals and order lineage, rather than decorative panels. See `docs/IMPORT_LAB.md` for the visitor path.

---

## v0.4 — Decision-oriented design principles

- **Deep navy (#122f3a):** trust, product framing, high-level orientation.
- **Indigo (#5368a8):** imported POS source records and integration-specific information.
- **Teal (#0c827b):** validated data, matched records, reconciliation success.
- **Amber (#b98131):** coupons, estimated costs, assumptions and experimental caution.
- **Muted rose (#b56d64):** financial exposure and validation risk—never automatically a bad result.
- **White / off-white:** readability of input workflows, metric panels and order audits.

The Campaign Lab page should convey *how to make a decision*: which POS data was analyzed, which coupons were matched, what costs were observed vs assumed, and what remains unknown. Keep real interactive orders visible instead of filling space with static imagery. Empty/invalid states and the explanatory labels are part of the visual design.
