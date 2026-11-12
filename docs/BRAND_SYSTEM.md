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
