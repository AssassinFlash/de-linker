# German guest inquiry chain, production acceptance 2026-11-05

Companion to `inquiry-guest-chain.md` (EN). Same criterion: a natural guest
inquiry on the German chain with zero blockage and zero errors.

**Result: PASS** (submission, German confirmation, locale and record all
verified; the test message's AI assessment took the designed unknown-retry
path, see below).

## Real submission (production, fresh guest, normal browser)

`https://de-linker.com/de/proforma-anfrage/`, no account, German form:

1. On-demand verification ran invisibly (Cloudflare challenge 200 →
   `protection/verify` 200), no interaction, no error.
2. Form POST → `302` → the **German** confirmation page
   `/de/proforma-anfrage/anfrage-eingegangen/8606/?key=…`
   (Checkout::received_url maps the confirmation to the German page).
3. Confirmation fully German: "Vielen Dank. Ihre Anfrage ist eingegangen.
   Anfrage-Nr.: 8606 … Wir antworten innerhalb eines Arbeitstags.",
   `html lang=de-DE`, German date/currency formats.

## Read-back

- Woo order 8606: `status=inquiry-received`, guest email, `OrderLocale`
  `de_DE_formal`.
- The artificial German test text was classified `unknown` by the AI mail
  assessment → the designed conservative path: receipt held, assessment
  retried on the Outbox backoff schedule (60s/300s/1800s/…), record retained
  for the team. This is the anti-abuse fail-safe, not a blockage: the inquiry
  is saved and stays in the team's queue. A normal business inquiry (EN 8603)
  classified `normal` and both mails went out within seconds.

## Cleanup (all read back)

- Pending assessment actions for 8606 unscheduled (0 left), order 8606
  deleted, `wc_get_order(8606)` → gone.
- `wp linker-commerce test-mail off` → success (normal routing restored).
- German confirmation screenshot:
  `~/de-linker-data/inquiry-readback-20261105/de-confirmation.png`.
