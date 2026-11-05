# Inquiry failure/recovery states, production acceptance 2026-11-05 (B line)

Companion to `inquiry-guest-chain.md`. Criterion: the customer chain covers
success AND failure/recovery states, not just the happy path.

**Result: PASS — verification failure is recoverable, entries survive, the
retry succeeds.**

## Real failure → recovery cycle (production, real guest form)

1. Filled the form (message/name/email/consent), then blocked
   `/wp-json/linker/v1/protection/*` at the client (simulated verification
   network failure) and submitted.
2. Failure state shown: "Verification could not be completed."; **the entries
   were fully retained** (message, email intact — the form-recovery behavior).
3. Removed the block and clicked Send again: verification completed
   (prepare/verify 200), POST 302 → confirmation inquiry **8608**
   (`inquiry-received`, correct record).

Screenshots: `~/de-linker-data/inquiry-readback-20261105/recovery-failed.png`
and `recovery-succeeded.png`.

## Read-back / cleanup

- Order 8608 saved as `inquiry-received`. Its artificial test text classified
  `unknown` → the designed assessment backoff (same as 8606); not a defect.
- Jobs unscheduled, order 8608 deleted, test mail OFF — all read back.
