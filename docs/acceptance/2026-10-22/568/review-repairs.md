# Fixed-source review and CI repairs (#568)

The first independent full-diff reviews used fixed `ba50de46`, with the same
`1f054757` implementation base. Spec reported five consumer failures; Standards
independently reported the VAT and Proforma index failures. Those findings were
reproduced with actual native WordPress/Woo consumers in the exclusive `b568`
instance before repair. This is local evidence, not deployed or inbox evidence.

| Finding | Native red seam | Repair and retained boundary |
| --- | --- | --- |
| First-save logical bytes excluded three trusted association values | The actual priority-100 first-save observer measured more bytes than reserved. Remaining full-payload bytes were tested at exactly one byte short and exactly equal, using the identical serializer and frozen prepared order. | Stamp REQUEST/INPUT/SUBJECT before explicit reservation; finalize actual complete metadata at the final pre-save hook. No customer field is truncated. The exact last-byte and no-native-row assertions remain. |
| Failed order binding was silently ignored | One native binding mutex failure let the original source claim received without a registry order association. | Binding failure throws into the native first-save owner; the tested failure leaves zero committed native orders. Verification also requires the actual saved ID to match the registry. Earlier durable pre-provider reservations remain charged when outcome is uncertain; this is not a universal failure-refund mechanism. |
| Changed email stranded the latest VAT notice | Full queue, native VAT verdict, native A-to-B email update, unchanged-VAT early return, then recovery previously produced no job. | Store a separate HMAC of unchanged VAT facts. Under the existing user lock, an unacknowledged current source may adopt the current email and a new version; capture and ACK must still match that exact current native source. Recovery makes one job, no second VIES request. Email changes during capture and erasure remain rejecting races. |
| Issued Proforma could miss its pending source | An early actual native status callback throws after real Issuer number/PDF/status persistence, before the email callback. | Issuer sets notification pending on that same original source before saving the issued data. Minute recovery rebuilds the one original job. The constant lives in Issuer, avoiding early autoload of a WC_Email subclass in independent native workers. |
| Stale/terminal Proforma rows starved recovery | A stale callback loaded before accepted ACK dirtied pending again; 64 older terminal/erased/accepted rows hid a later genuine source. | Fresh native source checks and pending changes share the existing source lock and native transaction. Query status and erasure before the 64-row bound; retire definite already-ACKed index rows without changing original jobs. Repeated recovery reaches the later valid source once. |

The original R1–R5 focused run passed 8 tests / 68 assertions after repair.
Private red logs retain the corresponding fixed-source failures, including the
corrected stale-object case whose pending value was originally `no` and therefore
actually became a dirty change in the failing implementation.

## Actual critical notification CI failure

Exact workflow run `39815794782` had a passing general check job and failed its
native mail group. Four original failures were reproduced locally. ReviewReminder
was creating a second unique Action Scheduler action after the shared JobStore
had already durably armed the original job. The duplicate API returned zero,
causing its source transaction to roll back instead of notifying the team.

ReviewReminder now reschedules that same original job, verifies one native
pending action, and reads back its exact state in NativeTransaction. A real outer
transaction is invisible to a second DB connection and rolls back job, source
state and AS together, with zero transport. A failed state readback also leaves
zero accepted handoff. The health endpoint test still requires authorization and
exact keys; it now asserts the intentional bounded `capacity_failure` shape,
timestamp and fixed reason rather than treating that new health field as a leak.
The combined focused run passed 23 tests / 239 assertions.

## Actual running-action retry seam

The wider native suite found another real scheduling failure. Action Scheduler's
`unique=true` predicate includes an in-progress predecessor. A retry called from
that running original action could therefore receive zero and leave no pending
successor after the predecessor finished. The existing real three-failure retry
and digest exhaustion tests exposed this; their assertions and delays are kept.

Reschedule uses a short original-job mutex, `FOR UPDATE NOWAIT`, the native
transaction and a non-unique AS insert, followed by an exact one-pending-action
readback. This permits the running predecessor while still bounding its pending
successor. There is no second mail job, new queue, new payload, retry budget
refund or external operation under this scheduling lock.

## Fixture defects separated from production failures

- Two LanguageLinks fixture email instances retained their constructor-registered
  receipt callbacks across tests, creating three actual receipts in later cases.
  Each fixture now removes only its own registered callback. Its own pre-mail
  collector also has exact teardown. Original one-receipt assertions remain.
- Digest's synthetic recipient-clearing callback previously survived an earlier
  assertion failure and poisoned later transports. Cleanup is now registered
  immediately. Its EN subject fixture temporarily chooses and restores EN team
  locale; its empty digest uses the existing native block clock seam instead of
  deleting the online snapshot's older inquiries.
- The actual Proforma link fixture now has native issued status before invoking
  that status-specific email. It asserts one actual tester delivery attempt and
  the source's accepted number beyond the preview capture.
- The reused local snapshot eventually had 128 native unhandled business rows;
  the final receiver correctly refused new normal requests before first save.
  Proof/NAT/campaign comparisons now use an explicit available normal pool only
  inside their restored fixture registry. Negative-cache initialization cases
  remain truly uninitialized. No original history was deleted, no production
  reader changed, and the dedicated capacity/disposition tests still read actual
  native historical debt and exercise full-count/byte refusal.

A temporary exact-`ba50de46` PHP control run on the same snapshot reproduced the
old mail-group failures. Private diagnostic harnesses separately confirmed local
SMTP capture and actual native mail were functioning. Neither the local transport
configuration nor assertions were weakened to accommodate a failing consumer.

This repair round changes no rendered customer layout or wording. The previously
captured 28 EN/DE desktop/mobile JPEGs remain the rendered evidence; native writer,
source, scheduler and fixture changes are verified separately. Full-diff Spec and
Standards review, exact new-head CI, current-main/#569 integration, fresh release
aggregates, production backup/readback and authorized inbox acceptance remain
coordinator gates.
