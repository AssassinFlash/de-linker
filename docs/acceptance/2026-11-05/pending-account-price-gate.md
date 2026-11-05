# Pending-account price gate, production acceptance 2026-11-05

Executor: main session. Criterion (owner 2026-10-17): a pending-approval
customer stays logged in, reads the site like a guest (no net prices), and the
account status is shown honestly.

**Result: PASS.**

## Real read-back (production)

- Fresh customer `pending947` (user 51, role customer, no approval meta →
  pending), real Chrome login at `/my-account/` succeeded (stays logged in).
- PDP `/product/saj-ats1-t63-a/` while pending: the price area shows
  **"Account under review. Prices after approval."** — no net price anywhere.
  The only € figure on the page is the public delivery-rate note (€14.90
  parcel rate), which is not a product price.
- Screenshot:
  `~/de-linker-data/inquiry-readback-20261105/pending-account-pdp-gate.png`.

## Cleanup (all read back)

- User 51 deleted, `wp user get pending947` → invalid (gone).
- Test mail was ON during user creation and switched OFF afterwards
  (option removed; normal routing restored).
