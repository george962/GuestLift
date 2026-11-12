# Five-minute GuestLift walkthrough

**Audience:** Restaurant marketing / finance / operations lead  
**Data:** Bundled fictional examples only

1. **The problem (0:00–0:45).** Open the homepage. Explain that different POS vendors encode orders and payments differently. Comparing raw exports is slow and prone to reporting mistakes.
2. **The approach (0:45–1:30).** Open How It Works. Click through sources, vendor adapters, the proposed GRDC format, storage, and shared analytics.
3. **Toast demonstration (1:30–2:30).** Open Demo. Select Toast, run the sample. Show standardized output and the counts for orders, net sales, discounts, and refunds. Call out an example order with multiple payments.
4. **Second vendor (2:30–3:30).** Switch to Square and run its sample. The values update, but the metric definitions and output fields remain the same.
5. **Explain auditability (3:30–4:30).** Open Canonical Records, select an order, inspect items and payments, and compare raw input vs GRDC output. Repeat a sample import to demonstrate duplicate prevention (API-connected mode).
6. **Next step (4:30–5:00).** This is a prototype, not a live POS integration. Ask whether source-independent, traceable reporting would solve a problem for the operator; a real pilot needs merchant consent and field-mapping validation.

If the local FastAPI backend is **not** running, the UI operates in **browser preview mode**. The visual flow uses pre-normalized bundled records; do not claim a live import or idempotency demonstration in that mode.
