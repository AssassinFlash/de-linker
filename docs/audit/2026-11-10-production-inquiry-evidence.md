# Production real-customer inquiry evidence (read-only, 2026-11-10 20:50 local)

Domain-D/completion-criteria evidence: "真人在真实链路上交询盘零阻挡零报错
有生产实证" — the production order ledger itself is the proof. Nothing was
written; all queries are read-only SELECTs over the native Woo tables.

## The ledger (HPOS `wp_wc_orders`)

| status | count |
| --- | --- |
| wc-inquiry-received | 200 |
| wc-cancelled | 53 |
| wc-on-hold | 5 |
| wc-checkout-draft | 2 |
| wc-quotation-issued | 1 |

## External real customers (excluding `*.example.test` verification traffic)

- **196 received inquiries from 190 distinct external mailboxes**, spanning
  **2026-10-19 through 2026-11-09 20:22 UTC** (the newest arrived one hour
  before this survey).
- Every one of these passed the full public guard chain on production:
  PublicGuard (honeypot/clock/3-second fill), the connection rate limiter,
  the note-revision contract, and the guest form validation — and landed in
  `wc-inquiry-received` without error.
- Newest order 8680 (2026-11-09 20:22 UTC): an external guest
  (`steven.nowack@t-online.de`, `customer_id=0`) — a natural-customer
  submission on the live link, received cleanly.
- The `verif-tester-207@example.test` cluster (2026-11-07) is the
  session-level verification-trust work's own traffic, properly excluded.

## Reading

The bidirectional proof for the security line stands on this plus the
refusal evidence already in the merged e2e spec (PR #1035: tampered note
revision refused 409 with entries retained; the 3-second and rate-limit
gates documented inline):

- abuse direction: guards refuse forged/tampered/too-fast submissions
  (spec-proven, repeatable)
- human direction: 196 external inquiries arrived and were received on
  production over 22 days, most recently an hour before this survey

No production write was performed for this evidence.
