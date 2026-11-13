# TableSignal v0.11 — Read-only AI intelligence

**Status: local development release candidate; not authorized for real merchants or live payments.**

TableSignal is a restaurant retention/discount decision-support product. This version adds the evidence graph and actual AI analyst in `/analyst`, makes Free versus Growth capabilities explicit on `/pricing`, and clarifies Square Sandbox versus future live POS integrations on `/connections`.

- Evidence: account-scoped Square Sandbox orders, observed order values, identity coverage, repeats, discounts and saved decisions.
- AI: OpenAI Responses API (`store=False`), server-side only. A verified Growth **test** subscription and configured API key/model are required. No raw order IDs/customer IDs are automatically sent.
- Actions: cost-scenario comparisons and persisted experiment drafts; no outbound marketing and no causal lift claims.
- Pricing: Explore is free with fictional data; $99/location/month is a **proposed future live price**; existing $149 local Stripe test subscription remains a test transaction.
- Live: no real POS connection and no real payment flow available in this build. See `docs/V011_AI_PRODUCT_AND_FIRST_CUSTOMER.md` for explicit go/no-go gates.

See `INSTALL_V011.md` for the direct-in-repository installation procedure.
