# Matrix findings F8/F9 verification, production 2026-11-05

Companion to `docs/acceptance/2026-11-04/full-matrix/DEFECTS.md` (branch
`acceptance/full-matrix-2026-11-04`). Two production-relevant findings from the
full-matrix pass re-verified on current production.

**Result: both findings are fixed/working on production.**

## F8 — registration website field, multi-label domains

- Current production `account-ui.js` `websiteOk()`:
  `/^[^\s/?#.]+(?:\.[^\s/?#.]+)*\.[^\s/?#.]{2,}(?:[/?#]\S*)?$/i` — the
  `(?:\.)*` group allows any label count; the scheme-rejection intent is kept.
  Multi-label hosts like `www.example.com` now validate.

## F9 — signed-in inquiry attribution and confirmation

Real production run with an **approved** test customer (user 52):

- Signed-in form submission → 302 → confirmation
  `/proforma-request/inquiry-received/8609/?key=…` shown (no redirect failure).
- Order 8609 `customer_id = 52` (correctly attributed), `inquiry-received`,
  account email; signed-in confirmation shows "View inquiries" (not the guest
  create-account CTA). Form prefilled name/email from the account.
- Bonus evidence: the approved account sees net prices on the PDP.

## Cleanup (all read back)

Order 8609 + user 52 deleted, jobs unscheduled, test mail OFF. Screenshot
`~/de-linker-data/inquiry-readback-20261105/signedin-8609-confirmation.png`.
