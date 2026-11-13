# TableSignal v0.10 — From restaurant data to a saved decision

**Scope:** local-only developer release. Stripe Sandbox and Square Sandbox; no production merchants, actual charges or marketing messages. Preserve the local `.env` and PostgreSQL Docker volume when upgrading.

## What this product sells

Restaurant **retention and promotion decision intelligence**. The first supported job is to help an owner understand available repeat-guest evidence, compare the costs of potential promotions, and save an explicit experiment draft. This is not another sales chart and it is not an autonomous marketing sender.

## Customer journey

1. Landing page: visit the public sample or create a private account.
2. Registration: local session established; `/account/welcome` confirms creation and points to business setup.
3. Restaurant onboarding: save name, restaurant type, and primary goal. The **plan choice and stage persist in PostgreSQL** across page refresh/navigation.
4. Subscription: optional Stripe TEST Growth checkout with verified confirmation `/billing/success`; return to billing to manage test subscription. Existing purchases can be reconciled without another checkout.
5. Data connection: Square Sandbox developer token or OAuth. No real POS or merchant PII. Sync completed orders and inspect sync history and its completion message.
6. Overview: private account metrics only, with honest empty states and a prominent **Review opportunities** action.
7. Opportunities: identify guest-ID coverage, repeat-visit evidence, observed discounts and what can/cannot be inferred from the sample.
8. Offer comparison: set hypothetical purchase count, basket, pre-discount margin and 10%-off or fixed-dollar offer. Read **discount expense** and modeled contribution **conditional on purchases occurring**; no uplift inference.
9. Saved experiment: store a draft in a tenant-scoped PostgreSQL table, revisit it in Experiments, change state between Draft, Planned and Reviewed. This does **not** send campaigns or claim they happened.
10. Return: sign out/sign back in; onboarding and saved decisions persist. Local session cookie expires after 30 days, and transient session fetch failures are retried instead of automatically treated as logouts.

## Navigation

Private application navigation: **Overview / Guests / Opportunities / Experiments**. Data connection, restaurant settings, account security, and billing are in the Account menu. Public demo is separate. `/account` now routes "Open workspace" to the private dashboard, not the sample demo.

## Metrics and limitations

- Store numbers derive from the authenticated workspace's Square Sandbox orders, not fake per-user seed data.
- Retention candidates are withheld when order history is too short/sparse; a historical order without a repeat is not enough to label a customer lost.
- Identified customers exclude anonymous transactions; no identity stitching and no consent assumptions.
- Offer calculations are scenarios, **not causal predictions, incremental sales, actual contribution or campaign ROI**.
- No automatic scheduled POS sync, full payment/refund reconciliation, promotional campaign execution or real customer contact permissions.
