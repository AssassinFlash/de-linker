# Inquiry chain walked end to end (2026-10-29, mission b2-inquiry / map #548)

The site's only business outcome — a visitor sends an inquiry and the team is
notified — had never been walked with evidence: the 2026-10-21 acceptance
(472) stopped before "Send inquiry" was clicked, and the 2026-10-22 production
check (522) stopped before any business form. This note records the full walk
on a local snapshot instance and what it found.

## Environment

- Worktree `/Users/chesterjohn/Documents/de-linker-worktrees/b2-inquiry`,
  branch `codex/b2-inquiry-chain`, base `origin/main` @ `a5cbb4026`.
- Local instance `b2inquiry` from snapshot `20261029-0433`
  (`just pull load b2inquiry latest`), WP 8895 / engine 8896 / genie 8897.
- Test-mail discipline (AGENTS.md §5): `wp linker-commerce test-mail on`
  before any submit; every outgoing email rewritten to the single tester
  address on the send path only — the queue keeps the original routing, which
  is what the routing assertions read. The browser fixture sets the same
  switch to `tester246@example.test`. Local isolation captures mail as
  `.eml` files (`~/de-linker-local/b2inquiry/mail/`); no mail can leave the
  host. No production system was touched; no mail was sent to
  sales@de-linker.com or any external address.
- Public protection mode is `off` locally (snapshot omits the operational
  options), so the walk exercises the legacy PublicGuard path — the enforce
  path was accepted on 2026-10-22 (522) and needs Turnstile, which local
  mode `off` intentionally bypasses.

## How the walk was driven

Standalone Playwright scripts under `tests/e2e/specs-walk/` (kept in the repo
as reproducible evidence tools; run with
`LINKER_E2E_INSTANCE=b2inquiry npx tsx tests/e2e/specs-walk/walk2*.ts`):

- `walk2.ts` — EN guest, `walk2-de.ts` — DE guest, `walk2-loggedin.ts` —
  logged-in approved customer, `walk2-dup.ts` — duplicate submit + empty
  draft after success. Each writes a JSON evidence file and screenshots to
  `.scratch/b2-walk/` (copied into `evidence/` here).

## What the walk proved (green unless noted)

### Guest, EN (evidence/en-guest.json)

- Form on `/proforma-request/` carries one draft line after add-to-cart.
- Invalid email: blocked client-side (native `type=email` plus
  `account-ui.js` `reportValidity()`), no POST leaves the browser.
- Submit inside the 3-second PublicGuard minimum: server refuses with
  "Please check your entries and send the form again." and **all entered
  values survive** the round trip (flash fields).
- Recovery submit → redirect `/proforma-request/inquiry-received/8500/`,
  success panel "Inquiry received / We reply within one business day." with
  the #533 deferred-receipt notice ("We have not sent a confirmation
  email." — mail leaves only after the pre-send verdict) and the
  "Create an account with this email" link.
- Order 8500: status `inquiry-received`, source `proforma`, 1 item, guest
  (customer 0).
- #533 chain: option `linker_inquiry_send_8500` pending → Action Scheduler
  `linker_inquiry_assessment_process` → Jev `typesafe/jev-1.13` verdict
  `normal` (escalated by deepseek-flash) → queue holds both mails with the
  original routing — team `to=sales@sunriverinverter.com` "New inquiry
  #8500 from Walk GmbH", receipt `to=<customer>` "Your inquiry #8500 has
  been received" → Outbox delivers both (`delivered_at` set) → two `.eml`
  files in the local spool, both addressed to the tester only.

### Guest, DE (evidence/de-guest.json)

- Same flow on `/de/proforma-anfrage/`: German validation copy
  "Bitte prüfen Sie Ihre Angaben und senden Sie das Formular erneut.",
  retained values, redirect `/de/proforma-anfrage/anfrage-eingegangen/8508/`,
  heading "Anfrage eingegangen", order 8508 `inquiry-received`/`proforma`.
- Queue routing captured: team "New inquiry #8508 from Walk GmbH", receipt
  **"Ihre Anfrage #8508 ist eingegangen"** to the customer address.
- **Delivered after the retry ladder:** the DE guest walk captured the queue
  routing (team + German receipt "Ihre Anfrage #8508 ist eingegangen") but
  its verdict outlived the walk's poll window. A follow-up DE submission to
  `/de/proforma-anfrage/` (order 8625, `lang=de`) went `pending → normal`
  within a minute and the Outbox delivered both mails to the local spool
  (evidence/de-delivery.eml.txt): team "New inquiry #8625 from Liefer Zwei
  GmbH" and the German receipt "Ihre Anfrage #8625 ist eingegangen" with
  German body ("vielen Dank für Ihre Anfrage #8625."), both rewritten to
  the single tester address. See "Findings" F1 for why first attempts
  sometimes need the ladder.

### Logged-in approved customer (evidence/loggedin.json)

- Profile row rendered collapsed (`<details>` closed) with billing prefill
  (name "Lena Login", email, company "Login GmbH") and consent pre-checked.
- Submit → success page; order's customer = the user id (not guest), 2 queue
  mails, both delivered, 2 spool `.eml` to the tester.

### Duplicate submit + empty draft (evidence/dup.json)

- Double-click on "Send inquiry": exactly **one** order results — order 8621,
  single success redirect `/proforma-request/inquiry-received/8621/`
  (client `accountState='submitting'` guard; the double click never produces
  a second order).
- Return to the form after success (draft emptied by the success path):
  resubmit refused with "Please add a product or write a message."
  (`linker_inquiry_empty` preflight), still exactly one order.

## Findings

- **F1 (reported, not changed — owner-approved constant):** the pre-send
  verdict's 10-second per-attempt window (#533, `Queue::WAIT_SECONDS = 10`,
  genie `WAIT_SECONDS = 10.0` "never renewed internally") is tight for
  German snapshots: primary Jev + deepseek-flash escalation measured 8.5–10.5
  s end to end (direct probe), so several first attempts return
  `unknown/deadline` and mail waits in the retry ladder (60 s → 300 s →
  1800 s → … → manual hold). EN snapshots passed first-attempt in all runs.
  The chain behaves exactly per spec #533 (fail closed, bounded native
  recovery, no substitute mail); whether to widen the window is an owner
  ruling, not a code fix, so nothing was changed here.
- **F2 (fixed in this branch):** `tests/e2e/specs/public-inquiry.spec.ts`
  still asserted mail in the queue immediately after submit — stale against
  #533's verdict-before-mail flow; the suite had not been run against an
  instance since. It now asserts the #533 deferral deterministically:
  immediately after submit the queue is empty, the receipt skip reason is
  `assessment_pending`, and the pages show the deferred copy (request door:
  "We have not sent a confirmation email." / "Es wurde keine
  Bestätigungs-E-Mail versendet."; contact door — which cannot yet know
  whether a receipt will follow — the plain "Thank you. Your message is
  with the Linker team." / "Vielen Dank. Ihre Nachricht liegt beim
  Linker-Team."). The verdict→queue→outbox delivery is timing-dependent on
  external models and is covered by the walk harness
  (`tests/e2e/specs-walk/`), not by the suite. Suite result: **16/16
  passed** (previously 16 failed / stale on main).
- **F3 (fixed in this branch):** `tests/e2e/specs/empty-draft.spec.ts`
  expected the DE create-account link to end in `/register/`; WooCommerce's
  German endpoint is `registrieren` (`/de/mein-konto/registrieren/`), so
  both DE tests failed on main. Expectations corrected per locale; 4/4 pass
  now.
- No product-code defect was found in the inquiry chain itself: both doors,
  both languages, validation, recovery, duplicate protection, prefill, the
  verdict gate and the outbox all behaved as specified.

## Commands

```bash
just pull load b2inquiry latest && just up b2inquiry && just serve b2inquiry
just wp b2inquiry linker-commerce test-mail on   # single-tester rewrite
cd tests/e2e
LINKER_E2E_INSTANCE=b2inquiry npx tsx specs-walk/walk2.ts            # EN guest
LINKER_E2E_INSTANCE=b2inquiry npx tsx specs-walk/walk2-de.ts         # DE guest
LINKER_E2E_INSTANCE=b2inquiry npx tsx specs-walk/walk2-loggedin.ts   # logged-in
LINKER_E2E_INSTANCE=b2inquiry npx tsx specs-walk/walk2-dup.ts        # duplicate/empty
LINKER_E2E_SKIP_SERVICES=1 LINKER_E2E_INSTANCE=b2inquiry npx playwright test specs/empty-draft.spec.ts
LINKER_E2E_INSTANCE=b2inquiry npx playwright test specs/public-inquiry.spec.ts
just wp b2inquiry linker-commerce test-mail off   # removed after the walk
```
