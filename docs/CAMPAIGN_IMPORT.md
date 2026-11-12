# GuestLift v0.4 — Campaign Import Contract

> **Data policy:** These upload screens are intended only for fabricated demonstrations. Do **not** import real restaurant customer records, card information, transaction exports, or email lists into the prototype.

## What the demonstration proves

An operator can provide transaction-like POS data and a separate campaign redemption log, then receive an auditable, descriptive summary of coupon redemptions, dollars discounted, related order sales, and repeat-purchasing coverage. It does **not** prove the campaign caused additional visits or profit.

## Required input files

### POS order sample files

Use `/import` to load the source-shaped data first. The built-in Campaign Lab already contains 56 fictional orders; you may also pick your last import in the browser. Local SQL matching requires the POS orders to have been saved to the local database before calling the campaign upload API.

For the bundled scenario, the Campaign Lab's **Save to local SQL** action imports the 28 Toast + 28 Square examples first, and then saves the campaign rows. For custom campaign files, your matching POS orders must already be in the local SQL demo.

### Campaigns.csv

| Field | Type | Meaning |
|---|---|---|
| `campaign_id` | Non-empty string | Stable synthetic campaign ID |
| `code` | Non-empty string | Displayed coupon/code label |
| `name` | Non-empty string | Human-friendly name |
| `offer_type` | `percent`, `fixed`, `free_item`, `other` | Reporting category only; no promotion is issued |
| `start_date`, `end_date` | `YYYY-MM-DD` | Inclusive validity window for recorded redemptions |
| `variable_cost_minor` | Nonnegative integer | **Assumed additional** cost per redeemed order, in cents; excludes the existing POS discount |
| `fixed_cost_minor` | Nonnegative integer | **Assumed allocated campaign expense**, in cents |
| `description` | Text | Scenario context; may be empty |

### Redemptions.csv

| Field | Type | Meaning |
|---|---|---|
| `redemption_id` | Non-empty string | Unique redemption event ID |
| `campaign_id` | Non-empty string | Existing ID in Campaigns.csv or database |
| `provider` | `toast` or `square` | Which POS namespace owns the order |
| `source_order_id` | Non-empty string | Exact ID for a previously ingested POS order |
| `redeemed_at` | ISO 8601 with UTC offset | Timestamp of synthetic redemption |
| `discount_minor` | Nonnegative integer | Coupon discount in integer cents, **recorded by the POS**, not newly applied by GuestLift |

CSV files must be UTF-8 with these exact headers; 2 MB / 2,000 rows per file maximum in this demonstration. They can contain extra fields, but additional fields are not currently used.

**Matching key:** `(provider, source_order_id)`; this prevents an order with the same ID under two POS systems from being confused. The demo permits **one campaign redemption per order** to avoid ambiguous discount allocations. Real stacked offers will need a more sophisticated model.

## Five-minute walkthrough

1. Visit `/campaigns`. Two sample campaigns and fictional POS data load automatically.
2. Download [campaigns-demo.zip](../frontend/public/samples/campaigns-demo.zip), then unzip it.
3. Upload `Campaigns.csv` and `Redemptions.csv` using the two file controls. Change the discount of one redemption or its referenced order ID to see the data-quality warning.
4. Switch between *Weekday lunch perk* and *Come back for more*; inspect matched orders, location summaries, and repeat-customer coverage.
5. Drag the assumed margin slider. Observe that **modeled** contribution changes while recorded discounts and sales do not.
6. If Docker is running locally, use **Save to local SQL**, then inspect `GET /api/campaigns/report` and `GET /api/customers/summary` at http://localhost:8000/docs.
7. Repeat the SQL import. New inserted-redemption count should be **zero** and duplicates should be reported rather than counted twice.

For a deliberate failure case, use [campaigns-broken-example.zip](../frontend/public/samples/campaigns-broken-example.zip). Its redemptions reference an unknown order and claim a discount larger than the order's recorded POS discount. Both should be rejected with row-level explanations.

## What the numbers mean

- **Redeemed orders** = count of distinct matched redemption events (one per order in this prototype).
- **Sales on redeemed orders** = total **pretax net sales** of those orders. Not sales caused by the coupon.
- **Recorded discount** = redemption amount validated against (and already included in) the source order's discount. This is a subset of POS discounts, **not** a second deduction from net sales.
- **Modeled contribution** = `round(attributed_net_sales_minor × margin% / 100) − (variable_cost_minor × matches) − fixed_cost_minor`. This is a scenario estimate, not actual measured margin or incremental ROI.
- **Repeat customers** = fictional identifiers with >= 2 observed non-voided orders across the selected imported dataset. **A customer is not matched between Toast and Square** merely because IDs look alike.
- **Unknown customer** is not treated as a new customer. Coverage is shown separately.

## Error and replay behavior

- Missing required headers, invalid UTF-8, oversized files, or malformed CSV layout result in rejection of the file set.
- Valid campaign/redemption rows can be accepted even when other rows are invalid; every rejected row is reported with a source file and line number.
- A redemption referencing a missing order, unknown campaign, voided order, outside-date event, or excess discount is rejected.
- Duplicate `redemption_id` values are rejected within a file. Re-importing identical previously persisted rows is counted as a **duplicate**, not a new redemption.
- A record with a previously used redemption ID but changed fields is rejected; a real correction/reversal workflow is **not implemented**.
- Existing campaigns with changed configuration are rejected rather than silently overwritten.
- The local API stores complete input campaign metadata, normalized redemption references, and a campaign import-run log.

## Not production ready

No authentication, no tenant isolation, no consent workflow, no source authorization, no production-grade financial reconciliation, no live vendor API connection, no audience/holdout assignments, and no causal experiment engine. Public hosting should use the **static frontend only**. A real pilot needs a separate architecture and security review.
