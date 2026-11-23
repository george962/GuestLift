# M6 — Engineering verification and external launch gates

M6 Step 1 merged in PR #33. This follow-up implements **steps 2–4 in one PR**.
It does **not** authorize Square production, Stripe LIVE or handling real merchant/guest data.

## Implemented engineering work

- Readiness/status displays: stale, importing, failed and disconnected data are never presented
  as reliable evidence for new recommendations. Operator pages point back to Square connections.
- Mobile navigation: keyboard Escape, visible focus and responsive, touch-sized actions;
  reduced-motion CSS. Playwright checks the core signed-in journey at mobile widths and runs
  axe serious/critical checks on key routes.
- Help and support: full Sandbox FAQ, authenticated support-request form, workspace-scoped
  storage and limits. There is no staffed support channel or email notification yet.
- Data portability: owner-only CSV ZIP for Square orders, refunds, decisions, selected locations
  and support tickets. No OAuth credentials or secret hashes in an export. CSV formula guards.
- Workspace deletion: the existing typed-name confirmation and workspace cascade remain. New
  support/telemetry/preview tables use `workspace_id` and are deleted with the workspace.
- Developer-preview acknowledgement: a recorded, versioned *Sandbox limitation notice* at
  signup follow-through; **NOT legally approved terms or marketing consent**.
- Minimal product events: allowlisted, deduplicated workspace+period signals for verified
  weekly-brief viewing, first verified insight, outcome viewing and client errors. No custom
  event properties, guest identities, email, raw URLs, prompts or stacks.
- Optional error tracking: the Next error boundary records an event (not a stack or user data),
  and the backend retains its existing request-ID logs. Production-grade Sentry configuration
  still requires a privacy and credentials review.

## Automated verification

1. Backend full pytest, including export and telemetry tests and migration drift tests.
2. Frontend unit tests, TypeScript checking, Next production build.
3. Local mock Square + real backend + Next browser journey, including developer-preview
   acknowledgement, Square OAuth, monitored selection, complete sync, brief and decision.
4. Playwright's narrow mobile viewport check; axe serious/critical WCAG checks in the
   signed-in journey. If these find violations, fix them before calling engineering complete.
5. GitHub CI, PostgreSQL migrations, container build and post-merge main CI.

## Remaining external gates (must remain open)

- Independent legal review and final consent/retention policy, privacy disclosures and terms;
  no legally binding consent is inferred from the developer-preview acknowledgement.
- Real Square Sandbox seller hosted on staging; Stripe TEST Checkout and Resend end-to-end;
  data-reconciliation accuracy against Square report.
- Lighthouse >= 90 mobile on public pages from deployed staging; manual and automated checks
  should be recorded with evidence, not presumed from a successful Next build.
- Three previously unfamiliar restaurant owners complete uncoached usability tests:
  find the sample value in <=2 minutes and connect their test seller unassisted.
- A staffed support route, SLA, admin ticket visibility and production error-monitoring config.

**Status convention:** M6 engineering can be complete when CI is green, but M6 customer
readiness is *not certified* until external gates above pass. Do not mark M7 ready yet.
