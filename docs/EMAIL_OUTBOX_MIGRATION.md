# Proposed migration: email outbox bookkeeping (for P0)

**Status:** proposed, not implemented. P2 (`fix/p2-email-validation`) fixed email delivery without changing the schema. Migrations belong to P0, so this note lists the columns that would make the current workaround simpler and easier to observe. Nothing breaks without them.

## What works today without a schema change
- `email_outbox.status` is a plain `VARCHAR(20)` with no CHECK constraint. It now holds `pending`, `sent`, `failed`, `expired` or `skipped`. Older rows may still say `not_sent`, and the code treats those as `pending`.
- **Retries:** the worker retries every pending row on each pass (every 10 minutes). It stops trying once a row is past its kind's delivery window: 3 days for a digest, 14 days for an outcome, 24 hours for a trial reminder.
- **Duplicates:** Resend gets an `Idempotency-Key` of `tablesignal-email/<row id>`. On Postgres, the worker also holds the row with `FOR UPDATE SKIP LOCKED` while it sends.
- **Recipient:** the code reads the member back from `dedupe_key`, using the formats in `emailer.digest_key`, `outcome_key` and `trial_key`.
- **Trial reminder preference:** reminders use the `outcome_emails` column, which is the switch their unsubscribe links have always turned off.

## Proposed revision `0009_email_outbox_delivery`

| Table.column | Type | Default / backfill | Replaces |
|---|---|---|---|
| `email_outbox.member_id` | `VARCHAR(36)` NULL, FK `workspace_members.id` ON DELETE SET NULL, indexed | Parse it from `dedupe_key` (formats above). Legacy `trial:<ws>:<days>` rows: match `to_address` to the workspace owner's email | Parsing `dedupe_key` in `_recipient_member_id` |
| `email_outbox.attempts` | `INTEGER NOT NULL` | `0` | Unbounded retries inside the window. Allows a cap such as 20 |
| `email_outbox.last_attempt_at` | `VARCHAR(48)` NULL | NULL | Lets the worker refuse to resend a row whose last attempt is older than Resend's 24h idempotency window (see residual risk) |
| `email_outbox.next_attempt_at` | `VARCHAR(48)` NULL, indexed together with `status` | `created_at` | Retrying every pass. Allows exponential backoff and honouring `retry-after` |
| `email_outbox.last_error` | `VARCHAR(200)` NOT NULL | `''` | Errors that only appear in worker logs |
| `email_outbox.sent_at` | `VARCHAR(48)` NULL | NULL | No record of delivery time |
| `email_outbox.status` | add `CHECK (status IN ('pending','sent','failed','expired','skipped'))` | `UPDATE email_outbox SET status='pending' WHERE status='not_sent'` first | Legacy value handling in `emailer.WAITING` |
| `workspace_members.trial_emails` | `BOOLEAN NOT NULL` | **Initialise from `outcome_emails`**, so anyone who already unsubscribed through a trial link stays unsubscribed | Trial reminders sharing `outcome_emails` |

Index: `ix_email_outbox_due (status, next_attempt_at)` for the delivery query.

## Code follow-ups once it lands
- `enqueue()` sets `member_id`, and `_recipient()` reads the column instead of parsing the key.
- `_attempt()` records `attempts`, `last_attempt_at`, `last_error` and `sent_at`, and schedules `next_attempt_at` with backoff.
- Map `PREFERENCE['trial_ending']` to `trial_emails`, and point unsubscribe tokens of kind `trial_ending` at it. Tokens of kind `outcome` that are already in inboxes keep controlling `outcome_emails`.
- Add a third toggle to `GET/POST /api/team/me/email` as an optional field, so the current two-field body stays valid.
- Remove `not_sent` from `emailer.WAITING`.

## Residual risk this would close
Suppose the worker crashes after Resend accepted a message but before the row was marked sent. If no worker then runs for more than 24 hours, Resend has forgotten the idempotency key and a retry can deliver a second copy. `last_attempt_at` lets the worker mark such a row `failed` with "delivery unknown" instead of retrying it.
