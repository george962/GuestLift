# Metric definitions — current demonstration

All data is synthetic. Currency is USD, integer cents in GRDC and SQL storage.

| Metric | Formula | Scope / caveat |
|---|---|---|
| `order_count` | COUNT distinct `(provider, source_order_id)` | All imported demo orders. Production must define voided/cancelled order exclusions. |
| `gross_minor` | Sum of item `gross_sales` or gross item prices | Pretax / excludes tips; each item counted only once. |
| `discount_minor` | Order-wide discount field | Used once, rather than adding it to any duplicated item-level representations. |
| `refund_minor` | Completed sample sale refunds | Assumed pretax refund only. Real tax/tip reconciliation not yet modeled. |
| `net_sales_minor` | `gross_minor - discount_minor - refund_minor` | Demonstration metric, not vendor-certified accounting revenue. |
| `average_order_minor` | `net_sales_minor / order_count` | Rounded to nearest cent for display. |

For Toast the adapter joins multiple CSVs by `Order Id` without multiplying parent order records. For Square it processes each order and separately matches payment/refund fixtures. Missing payment rows create warnings, not invented payments. API-connected metrics come from persisted canonical rows rather than React constants.

No loyalty ROI or contribution margin is claimed in the current release.
