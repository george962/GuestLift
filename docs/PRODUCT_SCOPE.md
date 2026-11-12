> **ARCHIVED: v0.2 planning notes.** See [current v0.5 roadmap](../ROADMAP.md) for active product scope.

# Product direction: GuestLift Restaurant Promotion Intelligence

## What we want to sell eventually

**Decision:** For restaurant operators, is it worth repeating a particular loyalty or coupon campaign, and where?

**Initial wedge:** Unified, trustworthy restaurant transactions and campaign economics for small and mid-sized multi-location operators. Compete on ease of onboarding, transparent financial metrics, and the ability to analyze multiple POS platforms—not on unproven claims that incumbents cannot perform incrementality testing.

## Current three-stage operator journey

1. **Data:** A merchant eventually uploads authorized Toast exports or connects Square via OAuth. Today `/demo` loads **bundled synthetic fixtures**, and the local backend parses these fixtures. Public uploads are disabled.
2. **Offer:** A manager defines a campaign name/code (e.g. `LUNCH10`), percentage/fixed discount or free item, minimum qualifying basket and unit-cost/margin assumptions. Today `/offers` is a **browser-only hypothetical scenario** using bundled sample orders. No coupon redemption joins exist.
3. **Decision:** The operator sees how many sample orders qualify, modeled offer spend, after-offer sales and a break-even threshold under explicit assumptions. Today it does **not** estimate actual customer response.

## How genuine loyalty analytics would work later

To move from illustrative economics to campaign performance, the next source contracts need: campaign definition and eligibility, order-level applied discount/coupon identifier, customer ID where legitimately available, channel, timestamp, actual variable costs and marketing expense. For incremental outcomes, use randomized eligibility/assignment (or a carefully justified causal identification method) and a valid control group. Coupon redemptions are **not** a substitute for randomization.

## Next build priorities, in order

1. **Publish and user-test** the public site, `/offers`, `/demo`, and `/how-it-works` on Cloudflare Pages.
2. **Test the merchant workflow** with 3–5 restaurant owners or marketing leads. Do they understand the value? Which provider do they use? Can they obtain order exports? Do their promotions have exportable codes or identifiers?
3. **Design an authenticated import pilot** (do not accept real data until privacy, access and storage controls exist).
4. **Implement provider-supported coupon linkage** and honest campaign reporting: redemptions, attributed orders, discount cost, with coverage metrics.
5. **Expand to randomized holdout experiments** and contribution-profit measurement once assignment logs and cost data are available.

## Out of scope in public v0.2

- Live Square OAuth connection, Toast enterprise API, production SQL hosting.
- User accounts, storing submitted coupon scenarios, collecting customer data.
- Official partnerships, external vendor certification, bank-linked rewards, or predicted incremental profit.

## Website navigation

- `/` — Owner-facing landing page.
- `/offers` — Coupon/free-item scenario with meaningful financial tradeoffs.
- `/demo` — How two unlike POS source formats normalize into GRDC.
- `/how-it-works` — Technical explanation for skeptical operators and analysts.

See `BRAND_SYSTEM.md` for the palette's semantic roles and `DEPLOYMENT.md` to publish the safe public version.
