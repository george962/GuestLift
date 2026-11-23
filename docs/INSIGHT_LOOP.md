# The weekly loop (M4)

**Discover → Investigate → Decide → Track**, built so the product never overstates what the data shows.

## Weekly brief (`app/weekly.py`, `GET /api/briefs/latest`)
- Compares the last complete week (Monday to Sunday, local time) with the average of the 4 weeks before, for all locations and for each location. Metrics: net sales, orders, average order, discount spend and the share of known guests who came back.
- A change is shown only when it is at least one weekly standard deviation from that average ("possible"), or two ("clear"). Otherwise the brief says nothing changed more than usual.
- Every finding includes its evidence: this week, the baseline, the % change, the normal weekly spread, the order count and the dates. Findings are ranked by money impact.
- Caveats appear when guest coverage is under 50%. The analyst prefixes answers with a data-status note when history is still importing or stale.

## Decisions and outcomes (`/api/decisions/plans`)
- A decision records what to measure, where (one location or all), the start date and when to read the result (2–8 weeks). The start can be in the past, so owners can log a change they already made.
- From the follow-up date, the readout compares the weeks after the change with the same number of weeks before.
  - It reports the % change and normal weekly variation, with a verdict: clear, possible or no clear change.
  - When last year's data exists, it subtracts the same weeks' movement last year, so seasonal swings aren't credited to the decision.
  - Every readout ends: *"This shows what happened after the decision, not proof that it caused the change."*

## Email (`app/emailer.py`)
- **Weekly brief:** Mondays from 7am in the restaurant's time zone, to every member who hasn't opted out.
- **Outcome readout:** on a decision's follow-up date, to owners.
- **Trial ending:** 3 days and 1 day before the trial ends, to each owner. These follow the owner's outcome-email switch, which is the setting their unsubscribe link has always turned off.
- Every email has a signed one-click unsubscribe link (`/api/email/unsubscribe`). Preferences live in Settings → Email.
- **Outbox:** the worker records each message once per recipient in `email_outbox`, then delivers it on the same pass or a later one.
  - A message waits as `pending` until Resend is configured (`RESEND_API_KEY` and `EMAIL_FROM`), or while Resend is down or rate limiting. It ends as `sent`, `failed` (Resend rejected that message), `expired` or `skipped`.
  - `expired`: it wasn't delivered in time. The limits are 3 days for a brief, 14 days for an outcome and 24 hours for a trial reminder.
  - `skipped`: the recipient opted out or left, or the trial reminder no longer applies.
- **No duplicates:** each send carries a Resend `Idempotency-Key` tied to the outbox row, so a retry after a timeout or a worker restart can't deliver twice. Postgres workers also lock the row while sending.
- **Preferences are checked again just before sending,** so unsubscribing also stops mail that is already queued.
- `run_due()` reports what this pass queued and what happened to it: `sent`, `failed`, `expired` and `skipped`, plus how many are still `pending`. `emailer.outbox_counts()` gives totals by status, and older `not_sent` rows count as pending. The worker logs both.
- Addresses come from the local account, or from Clerk's verified primary email (`CLERK_SECRET_KEY`).
- Schema follow-ups (attempt counts, backoff and a separate trial-email switch) are proposed in `docs/EMAIL_OUTBOX_MIGRATION.md`.

## Analyst evaluation suite (`tests/test_analyst_evals.py`)
- Runs 7 data situations × 6 questions = 168 checks in CI. The situations are typical, no data, low coverage, skewed locations, refunds, heavy discounts and all-anonymous.
- The checks:
  - every number in an answer comes from the verified summary
  - evidence keys exist
  - no causal language
  - missing data is said plainly
- It must score 100%. A self-test confirms the suite fails on a fabricated number.
