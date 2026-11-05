# Natural guest inquiry chain, production acceptance 2026-11-05

Executor: main session. Completion criterion (owner 2026-11-04 first
principle): a natural guest submits an inquiry on the real production chain
with zero blockage and zero errors, with the mail discipline intact.

**Result: PASS.**

## Real submission (production, fresh guest, normal browser)

Real Google Chrome (normal presentation), `https://de-linker.com/proforma-request/`,
no account, fields: message, name, email, company, consent:

1. On-demand verification ran **invisibly**: `protection/prepare` 200 →
   Cloudflare challenge 200 → `protection/verify` 200. No checkbox, no click,
   no error. (The challenge stalls only automation-flagged browsers; a normal
   browser needs no interaction.)
2. Form POST → `302` → confirmation page
   `/proforma-request/inquiry-received/8603/?key=wc_order_euf1WOgrPUwfZ`:
   "Thank you. Your inquiry has been received. Inquiry no.: 8603 … We reply
   within one business day." Customer saw no error at any step.

## Read-back

- Woo order 8603: `status=inquiry-received`, billing email the guest address,
  total €0.00, guest customer.
- AI mail assessment (the correct model channels): Jev primary via OpenRouter
  (0.22s) + deepseek-flash escalation via the official API (4.0s), decision
  `normal`, completed in 5.8s.
- Mail log (`wc-logs/linker-mail-2026-11-05-…log`): **both** messages sent —
  internal "New inquiry #8603 from Acceptance Test GmbH" and customer
  "Your inquiry #8603 has been received". Test mode was ON: every delivery
  went to the tester address `chester@de-linker.com`, exactly one copy each.
- The confirmation page's transient "We have not sent a confirmation email."
  is the honest assessment-pending state (`ReceiptLimit::SKIPPED_META`);
  ~6s later the receipt was sent and the meta cleared. Not a defect.

## Cleanup (all read back)

- Order 8603 deleted (`delete(true)`), `wc_get_order(8603)` → gone.
- `wp linker-commerce test-mail off` → success; option removed, verified.
- Confirmation screenshot:
  `~/de-linker-data/inquiry-readback-20261105/confirmation.png`.
