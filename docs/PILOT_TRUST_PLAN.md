# Pilot trust plan — real restaurants, real Square data

**Goal:** 3–5 real Square restaurants connect read-only for 6 weeks so we can prove three things, in this order:
1. **Safe:** their data is protected, minimal, and deletable — and they can verify that.
2. **Accurate:** our numbers match Square's own reports.
3. **Useful:** the weekly brief changes at least one real decision per restaurant.

Companion to `docs/PRODUCT_PLAN.md` (M3, M6, M7). No real data is accepted until **Gate P0** below is fully checked.

## 1. Ask for as little trust as possible: the trust ladder

| Level | What the owner gives us | What we learn | When |
|---|---|---|---|
| 0 · Demo | Nothing — fictional sample workspace | Do they get the concept in 2 min? | Now |
| 1 · Concierge review | A Square report export (Sales Summary, Items, Discounts) they choose to send; no account access | Would a hand-written brief be useful? Which questions matter? | Weeks 1–2 |
| 2 · Read-only connection | Square OAuth with read-only scopes, revocable any time | Does the automated pipeline match Square, and do they use the weekly loop? | Weeks 3–8, after Gate P0 |
| 3 · Paid | A subscription | Willingness to pay | After the pilot review |

Each level must succeed before asking for the next. Level 1 tests usefulness without any data-access risk, so it starts immediately.

## 2. Gate P0 — must be true before the first real connection

### Data safety
- [ ] **Read-only scopes only:** `MERCHANT_PROFILE_READ ORDERS_READ PAYMENTS_READ`. No write scopes in the pilot. A test fails if the requested scope list changes.
- [ ] **Data minimization:** store only order IDs, location, timestamps, money amounts and Square's pseudonymous `customer_id`. No names, emails, phone numbers or card data. A schema test fails if a column with personal-data naming is added without review.
- [ ] **Tokens encrypted at rest** (Fernet, already implemented); key held only in the host's secret manager; documented rotation procedure exercised once.
- [ ] **Tenant isolation:** every endpoint covered by an isolation test (PRODUCT_PLAN M2 route inventory).
- [ ] **AI boundary:** only verified aggregates leave our system, with provider data retention off (`store=False`); or the LLM stays disabled for the pilot. Pilot owners are told which.
- [ ] **Access control:** MFA on GitHub, Render, Neon, Clerk, Square Developer, Stripe, Sentry and email. Only the founder has production database access; access is logged.
- [ ] **Deletion works:** disconnect deletes the token immediately; all imported data is deleted within 7 days (or immediately on request). Tested end to end, including backups policy.
- [ ] **Backups:** encrypted, daily, and one restore exercised.
- [ ] **Incident response:** a one-page plan; affected owners notified within 72 hours of a confirmed incident.
- [ ] **Errors and logs carry no order or customer data** (request IDs only); Sentry PII scrubbing on.

### Legal and paperwork
- [ ] Privacy Policy and Terms, reviewed by a lawyer.
- [ ] A one-page **pilot agreement**: free, read-only, purpose limited to providing them the service, no selling or sharing data, deletion on request, either side can stop any time.
- [ ] Square developer terms reviewed for a production app (a private app used by invited merchants; App Marketplace listing is not needed for this — confirm with Square's current terms).
- [ ] Consider cyber-liability insurance before connecting more than one restaurant.

### Accuracy — engineering fixes found while writing this plan (go into PRODUCT_PLAN M3)
- [ ] **Order volume limit:** sync currently stops after 800 orders per batch of locations (8 pages × 100). A busy restaurant exceeds that in a week. Replace with a checkpointed backfill worker.
- [ ] **Local time:** daily metrics bucket by UTC date (`insights.py`). Square reports use the location's time zone. Bucket by each location's `timezone`.
- [ ] **Refunds:** not reconciled today, so revenue can be overstated. Import refunds and report net-of-refunds sales.
- [ ] **Service charges, voids, split tenders and gift cards:** handled explicitly or shown as a known gap, never silently miscounted.
- [ ] **Production Square environment** switch (still gated), hosted pilot environment on HTTPS, separate from staging.

### What we say
- [ ] **Claims register** (`docs/CLAIMS.md`): every claim on the site and in briefs, with the test or evidence behind it. Remove anything we can't back.

## 3. Proving accuracy with each restaurant (week 1 of Level 2)

For each location, over the same date range and the location's time zone, compare against Square Dashboard → Reports → Sales Summary:

| Measure | Pass |
|---|---|
| Completed order count | Exact match |
| Gross sales, discounts, refunds, net sales, tax, tips | Within ±0.5%, with every difference explained |
| Daily totals | Match on every day of a full week |

We review the comparison *with the owner*, in a 20-minute call. The pass/fail record is kept per location. Any failure blocks that restaurant's weekly brief until fixed. This becomes an automated reconciliation report in M3.

## 4. Proving usefulness

- **Before connecting:** a 30-minute interview. What decisions they make weekly, what they wish they knew, and how they decide on promotions today.
- **Weekly:** brief delivered; a 15-minute check-in. Did anything in it change what you did? We log decisions and outcomes.
- **Success for one restaurant:** acts on at least one insight, says they'd be disappointed to lose it, and names a price they'd pay.
- **Pilot success:** at least 3 of 5 meet that bar, and the data-trust record is 100%.
- **Stop or rethink if:** after 4 weeks, nobody has acted on a brief, or accuracy can't reach the bar for a common setup.

## 5. Finding restaurants and earning trust

**Who:** independent Square restaurants with 1–5 locations, using Square Loyalty or emailed receipts (so guest data exists), an owner who answers their own email, and who runs promotions.

**Where:** warm introductions first — friends, local restaurant groups and associations, restaurant accountants and bookkeepers, Square implementation consultants. Then local in-person outreach. No cold mass email.

**What we offer:** free during the pilot plus a discounted first year; a hand-checked weekly brief; direct founder access.

**Materials** (before the first conversation):
- A one-page "What TableSignal can and can't see" sheet. Show the exact Square permission screen, what we store, what we never store, and how to revoke access (Square Dashboard → Account & Settings → Apps).
- The public demo link, and a sample brief built from fictional data.
- The pilot agreement and privacy policy.
- A named human contact with a phone number.

**Trust behaviours:**
- Show the reconciliation results; don't just claim accuracy.
- Say clearly what we don't know, such as low guest-identification coverage.
- Confirm deletion in writing when an owner leaves.

## 6. Sequence

| Weeks | Work | Exit |
|---|---|---|
| 0–2 | Interviews and Level 1 concierge reviews (no access needed) while engineering builds Gate P0 items (M2 identity, M3 pipeline fixes, legal) | 5+ interviews done; Gate P0 checked |
| 3 | First restaurant connects; reconciliation call | Accuracy bar met |
| 4–8 | Add up to 4 more; weekly briefs and check-ins | Usefulness bar measured |
| 9 | Pilot review against `docs/V013_TO_V1_PRODUCTION_GATES.md` | Go / iterate / stop decision |

## 7. Owner decisions needed

- Who signs the pilot agreement for TableSignal (a legal entity is needed before real data — LLC or similar).
- Budget for a lawyer review and insurance.
- Whether the AI analyst is on or off during the pilot. Recommend **off** until the evaluation suite (M4) passes.
