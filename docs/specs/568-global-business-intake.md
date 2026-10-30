# Shared business reception and notification occupancy (#568)

## Problem and scope

A successful public proof did not bound ordinary accepted business growth.
Changing cheap identities, wording or the landing domain could keep creating
complete inquiries and their notification jobs. The exact campaign sampler,
verification review lane, provider budgets and SMTP attempts each protected a
different consumer; none established a general persistent business envelope.

Five real business actions share the new site counters: `contact`, `inquiry`,
`genie_contact`, `genie_inquiry`, `conversation_mail`. Existing nonce, proof,
ownership, browser/account/connection and native field checks remain. Normal
browsing receives no additional challenge. Jev cannot delete native inquiries,
release business capacity or decide a customer is trusted.

**Current integration authority (2026-10-23):** the owner superseded the original
label-only delivery policy. The existing mandatory pre-send permission remains
authoritative for team inquiry mail, customer receipts and conversation copies.
A complete public submission is persisted immediately; classification runs in
the background. Unknown, malicious, unavailable or invalid evidence cannot send
mail or consume receipt/transport allowances. Only the already confirmed static
campaign is synchronously rejected by the existing required-proof/Campaign v3 gate.

This ticket bounds business reception and the final native mail-job writer.
It does not claim that every WordPress table or every public account is bounded.
The separate registration capacity ticket #569 owns pending-account reception.

## Initial operating choices

The coordinating owner approved these adjustable allocations on 2026-10-22:

| Pool | Site throughput | Unhandled native inquiries | Pending native notification jobs |
| --- | --- | --- | --- |
| Ordinary | 16 per fixed hour; 64 per UTC day | 128 and 32 MiB logical encoded data | 192 and 48 MiB encoded messages |
| Staff-approved customer | 8 per fixed hour; 32 per UTC day | 64 and 16 MiB logical encoded data | Uses ordinary notifications unless a native critical producer applies |
| Native critical mail | Separate existing priority context | Not a second inquiry pool | 64 and 16 MiB, including unused pre-reservations |

These numbers are operational choices, **not** an industry standard or a
verified customer-demand peak. Ordinary full capacity temporarily prevents a
new ordinary submission; zero false refusal or zero friction is not promised.
The independent approved reserve protects genuine staff-approved accounts.

The 192-job choice leaves headroom against the existing standard SMTP attempt
allocation of 360; that arithmetic is not evidence of real customer volume.
The byte envelopes initially allocate 256 KiB times each count. **256 KiB is not
a per-record limit.** A complete larger lawful inquiry/job can consume remaining
aggregate bytes. The review lane's existing 20-line/32-KiB shape is not copied
to ordinary verified business reception.

The private pre-incident snapshot contains 74 older inquiries, with day counts
5, 1 and 3 for October 19–21, plus 88 incident-window inquiries. These aggregates
include synthetic acceptance and unverified records; a denominator of confirmed
real customers is unknown. The historical note/meta sample was 617,113 bytes,
maximum 83,087 and p95 39,553, with at most 11 product lines. This excludes some
native address/item/index/page storage and is not a physical database estimate.
It supports measuring real shapes rather than silently truncating legal drafts;
it does not prove the chosen site throughput is sufficient for every future peak.

## Authority and no free reset

`TrustedCustomer` requires a plain native Woo customer, native approved status,
a positive approval timestamp and `changed_by` pointing to a real employee with
`manage_woocommerce`. Self-approval, a pending/restricted account, VAT text,
login, a non-customer role whose Approval class defaults to approved, and a Jev
label never grant the reserve.

All five actions use the same site identity in `BusinessPolicy`. Cheap browser,
email, connection, action, language and message changes do not renew site
throughput. The native ledger retains its dispatch/replay rules and login carry.
A reused operation recovers its actual native result before new admission; it
cannot obtain a new free record after an approval/pool change. An already charged
entry is never moved to another pool merely because the account changes.

## Final native inquiry boundary

`BusinessCapacity::prepare` runs before Woo's first save and is called explicitly
from Sender as well as the native order-save hook. Calling it only from the hook
would be insufficient: Woo catches some save exceptions. Its registry stores
only operation references, pool, native order ID and logical byte count. The
complete ordinary content remains in Woo, not another body queue.

`bytes` encodes current native order properties, complete billing/shipping,
items and their metadata, handoff, snapshot and local customer evidence. Pending
`WC_Meta_Data` values must be read through their current getters; its JSON
serializer can expose the older snapshot. Native row IDs and generated dates
are excluded from this logical business accounting. This is not an estimate
of InnoDB pages, indexes, uploaded attachments or future staff document storage.

The same native IntakeStore mutex/CAS atomically reserves count and full logical
bytes. New business/mail edits may wait at most one second for that short DB-only
section; the inherited review default remains zero. A row owned by an uncommitted
outer transaction is still read with `FOR UPDATE NOWAIT`, so it cannot hold a
public request until the server's long lock timeout. No global capacity mutex
spans optional summary HTTP, model dispatch or SMTP. Native two-connection
fixtures prove final count/byte winners and query actual lock ownership during
the provider seam and PHPMailer transport.

Business first-save alone may use that one-second budget to recover MySQL error
3572: it releases the named IntakeStore mutex, briefly backs off and retries so
the transaction that already owns the option row can reach its final bind and
commit. This avoids inverting the named mutex and row lock while preserving the
actual capacity answer. Mail capacity and other IntakeStore consumers keep the
immediate `NOWAIT` failure path; an unrelated open outer transaction must not
make their public worker wait.

The trusted REQUEST/INPUT/SUBJECT association is stamped before explicit byte
reservation. The final pre-save hook rechecks the complete actual metadata with
the identical serializer; exactly one missing byte refuses the complete record.
Native binding failure propagates to the first-save owner, and verification
requires the registry to reference the actual saved order ID as well as all
expected metadata. Sender never claims success solely from its in-memory Woo
object. Earlier durable pre-provider reservations remain charged on uncertain
failures; no general automatic time or exception refund is introduced. After provider work ends, Sender starts a short fenced native transaction
covering first save, native received status, source metadata and any synchronous
notification handoff. A known exception before commit rolls back that native
phase. A lost commit remains uncertain, with no fabricated received result or
automatic refund of the earlier durable reservation. Native HPOS metadata
uses TEXT, so the large-payload acceptance deliberately uses multiple lawful
fields rather than relying on a single field beyond native storage capacity.

## Optional paid summary envelope

The existing optional summary capability is retained. Before dispatch, Sender
prepares and freezes the complete native draft/context, reserves that complete
base plus the legal generated-summary envelope, releases the site mutex, then
calls the existing Tools summary filter. Before first save, actual known bytes
replace only unused generated-summary slack; the slot and dispatched throughput
remain charged. Model failure follows the existing optional fallback semantics
and preserves the customer's original full message.

The authoritative existing Tools schema is 800 summary characters, 500 note
characters, six conditions of 120 characters each and 12 quantity rows with two
positive PHP integers. The summary has three copies: order summary metadata,
Queue snapshot submission and local CustomerEvidence request. Frozen context
elsewhere is already included in the measured base and is not rebuilt after the
provider returns.

The upper shape uses six JSON bytes per character (U+0001) and PHP_INT_MAX's
19 digits on this PHP 8.3 substrate. Reasons are limited to native fixed
`no_service_url`, `unreadable`, `http_100` through `http_599`, or
`transport_error`; arbitrary WP_Error diagnostics are not customer content and
cannot make this envelope unbounded. Customer words, summary, note, conditions
and quantities are unchanged.

A native 2026-10-22 measurement produced 13,028 bytes for maximum summary JSON,
39,193 additional reserved bytes for all actual native wrappers/copies plus
72 bytes for three possible refreshed timestamps, and 41,678 actual complete
bytes on a 2,557-byte synthetic prepared base. These are a repeatable sample
of the serializer, not a fixed per-inquiry cap. Native tests check actual schema
constants, maximum field shape, all three copies, unsaved refusal before the
provider seam and actual bytes fitting the reserve. Order cloning requires
native `init_meta_data` for independent metadata because WC_Abstract_Order
intentionally overrides base deep-cloning behavior.

Held review also retains optional summary. Intake persists a `creating` entry
under the short global mutex, holds only an operation-specific mutex while work
runs, then binds under another short global edit. An exact saved
`BusinessRecord::REQUEST` can recover the original order after a crash. If work
started but no exact native source can be found, its paid/native outcome is
unknown: the creating slot stays charged and the same operation cannot freely
dispatch again. Elapsed time does not make this safe to refund.

## Notification ownership, transactions and recovery

The stable critical interface is defined in [568-critical-reservation.md](568-critical-reservation.md).
The final JobStore writer charges complete `Message::to_array()` JSON under the
same capacity registry and a native transaction/savepoint. Only a positive native
job whose full content/source read back correctly is accepted. Count, bytes and
critical pre-reservations are atomic. Ordinary full capacity never consumes the
critical reserve; staff promotion atomically moves the same held job, or leaves
it ordinary and held if critical is full.

Outside an outer transaction, Outbox attempts delivery immediately after durable
handoff. Inside one, job/capacity/source ACK and scheduled action join the caller,
and transport waits for a committed independent consumer. The shared mutex wrapper
owns no transaction and must never roll back unrelated caller data. A consumer
rolls back only its own transaction/savepoint. Native tests prove both successful
rollback/commit and callback/read failures with unrelated outer data visible only
to the owner until its explicit commit. An owned COMMIT must be confirmed before
transport. An unconfirmed result is not a reason to create another shadow job.

Every new ordinary inquiry freezes its existing Queue snapshot and mandatory
send-policy marker before first save, regardless of the legacy label-display
setting. `PENDING=yes` covers classification and the unacknowledged durable
notification handoff. No `notification_only` bypass is introduced.

Each background classifier attempt has the existing ten-second model window
from that attempt's start; queue delay does not consume it. The same authoritative
source, routing, current private data and exact final `Message` are rechecked at
every SMTP/PHP budget boundary. Receipt reservations occur only when a normal
source prepares its actual receipt. Unknown/malicious sources retain their saved
content and business count/bytes; bounded existing classification recovery does
not refund them or default to sending.

A valid normal verdict can remain `approved` when the final job pool is full.
Recovery reuses that source-bound verdict only while all authoritative inputs
still match, then atomically creates the original team/receipt jobs and source
ACKs. It does not repeat the model just to retry a failed native handoff. Erasure,
changed source/routing and old unbound jobs cannot inherit permission. The original
38 held jobs retain their metadata and remain held; capacity installation is not
a release operation.

| Native producer | Before-side-effect / recovery contract |
| --- | --- |
| Ordinary team inquiry | Mandatory source-bound classification, exact Message permission and atomic original job/ACK; approved native handoff recovery without another model |
| Inquiry customer receipt | No receipt allowance before normal permission; full original template after normal, atomic receipt job and source ACK; existing no-confirmation fact while pending |
| Registration team + received acknowledgement | #569 owns exact operation/user binding and independent optional count-1 critical pre-reservations; current configured acknowledgement lifecycle is retained |
| Staff approval | Preview/pre-reserve complete native Message; account, reason, audit/session mutation and staged original mail job join one fenced native transaction; a false staged handoff aborts the change |
| Core/Woo password reset | Preview before key mutation; exact server scope joins native key writer to original job/AS; confirmed commit precedes transport; actual Woo false result returns to the original form with retained username/email and native error notice |
| Proforma issued | Existing issued native order/PDF plus explicit notice pending; job/source ACK atomic; minute recovery rebuilds pending notice once |
| Genie address confirmation / conversation copy | Fixed native confirmation remains a separate trusted purpose. Shared conversation content returns accepted / pending / refused accurately; confirmed guest token ACK, frozen source, original pending job and capacity join one transaction. Full/no-handoff retains the link; normal exact-message permission is still required before text delivery |
| VAT verdict-change team email | One current source version plus pending association commits with native verdict fields after VIES; exact-generation job ACK; minute recovery of latest current state without repeating VIES; historical intermediate events are not replayed |
| Daily digest | Rebuilds current state on next daily run; a past refused digest is not automatically reconstructed as the same event |
| Service health alert | Critical producer, repeats on a later failing health tick; an individual refused alert has no automatic past-event reconstruction |
| Core payment-gateway-enabled admin email | Native post-write producer without a reliable preflight/rebuild source; explicit false plus bounded health exception |

CapacityHealth retains one fixed-size private failure record and sends no alert
email, so capacity exhaustion cannot create a recursive mail storm. Held,
failed and ambiguous jobs remain charged. Core `deleted_post` fires before cache
cleanup; native deletion readback explicitly clears the stale post cache before
confirmed absence releases mail occupancy.

### Original connection and committed recovery

WordPress can reconnect after SQL error 2006 and replay the failed statement in
new-connection autocommit. A later successful ROLLBACK is not evidence that the
old writes rolled back. `ConnectionFence` temporarily sets the original wpdb
client's reconnect retries to zero, enables strict native mysqli errors before
every scoped query, and checks the original client/handle/server connection ID.
Nested scopes restore the previous driver policy in LIFO order; no global database
or WordPress setting is changed. A lost connection cannot trigger compensation
writes on a replacement client.

`NativeTransaction` retains the original generated savepoint through native
writes, verifies that exact point before commit, confirms that an owned transaction
ended, and never commits a caller's transaction. Its optional after-commit callback
passes only an original job ID to the existing consumer. It runs only after a
confirmed owned commit; unknown/rollback runs no transport. An unmanaged outer
transaction keeps its durable AS consumer until an independent committed reader.

Every new native JobStore job, source ACK, capacity change and unique original-job
AS action commit together. The recovery action is not added later by a potentially
crashed producer. Retrying changes only that job's pending action atomically; a
confirmed successful send removes only its own pending action. Existing held jobs
are neither armed nor changed by importing debt. Same-job mutexes serialize the
immediate and scheduled consumer, so the initial recovery action cannot race a
slow immediate transport into a duplicate send.

Native fault fixtures use real local server-side KILL before the first write and
after partial writes, actual server COMMIT followed by lost acknowledgement, and
SIGKILL of a separate PHP worker after committed handoff but before transport.
They check independent database visibility, original source/job/AS, no partial
native record, retained unknown reservations and one original recovery consumer.
These tests do not kill production connections or send real mail.

Password-reset handoff failure is captured through Woo's real `email_sent(false)`
consumer: its original action otherwise returns true unconditionally. Only an
exact current server reset reservation can activate this branch. A proven failed
handoff rolls back the native key write; a lost commit stays unknown. The failed
Woo request saves only the existing username/email field in FormRecovery, adds the
already reviewed native error notice and returns with HTTP 303 to the native
lost-password URL. The before/after native form hooks use WordPress's HTML tag
processor to restore only that input's value; template structure, styles and key
validation remain native. Core WordPress retains its existing false-mail error.

## Release, privacy, migration and rollback

Only verified employee native Proforma issued, completed or cancelled disposition
releases unhandled inquiry occupancy. Proforma is the website's completed
handoff because subsequent trade is offline. Client cancellation, model labels,
SMTP success and clocks do not release it. Actual native deletion may release
removed storage. Throughput already dispatched is never refunded by a later
status change or deletion. Privacy erasure strips PII/retry associations but
does not refund unresolved occupied capacity.

First initialization imports all native still-open ordinary inquiries and all
actual private/failed/held mail jobs as historical debt under the lock. Old held
incident jobs are not deleted, rewritten or resent. Historical excess is retained
and blocks new affected writes until actual processing creates room. A legacy
record is ordinary unless it has native priority provenance; pending-account
registration is not staff trust.

### Exact historical debt and guarded staff disposition

The private unmodified 2026-10-22 14:08:10 UTC native SQL snapshot has SHA256
`d449cea25020922f412eeadeae2e13fa3bd83c3bd9295905c4eb61ea0a94e55c`.
It was imported into a separate local schema for native aggregate analysis:

| Snapshot debt | Count | Complete logical encoded bytes |
| --- | ---: | ---: |
| Ordinary legacy inquiries | 102 | 394,625 |
| Of those, not currently held | 64 | 231,483 |
| Of those, held | 38 | 163,142 |
| Separate native review records | 3 | 6,931 |
| Original held mail jobs | 38 | 438,262 |

No legacy account is inferred to be staff trusted. Ordinary initially has 26
of 128 slots free in that snapshot; its 38 held mail jobs occupy the ordinary
192-job envelope and have attempt count zero. These are exact logical serializer
measurements at that snapshot time, not current production counts or physical
InnoDB sizes. A later independently observed 24-message attack using another
landing host is outside this snapshot and outside this disposition manifest;
release requires a fresh authoritative aggregate, not these stale remaining slots.

Only the original 87 individually verified exact campaign bodies are eligible
for the owner-approved one-time staff disposition. Controlled record 8037 is
explicitly excluded. All 87 native snapshot body SHA256 values match the earlier
private incident manifest and the native complete customer note; all satisfy the
exact anchored Campaign predicate. A held flag by itself grants no exclusion.
The private guarded manifest SHA256 is
`451978ea1d1be0901d37e8a4302c00e1cbb973d7092c012b7b348ebc29977eee`.

`tools/security/568-disposition.php` first validates that exact 87-entry manifest,
its SHA, operation UUID, native body hashes and current exact campaign match. The
actual staff-only apply/rollback writes one native private order note and signed,
body-bound disposition metadata per transaction, with precise confirmed/partial
results. It does not change Woo status, customer text, notification hold, existing
job content/status/attempts, privacy data or throughput. Unknown commit is not
reported as all-batch success and is not compensated on a replacement connection.
Rollback removes only this operation's new exact note/marker/index and restores
its unhandled debt, preserving the original business record.

The bounded historical index contains at most 87 IDs. Every relevant short
capacity read validates authoritative native marker, staff, private note and full
body binding. Missing/changed note, body or marker returns that record to ordinary
debt, including when an older registry snapshot is restored. Historical held
records are never automatically excluded by their notification flag.

A disposable full native clone applied all 87 dispositions, read the normal
capacity decision in a fresh PHP process, and rolled all 87 back. Applied ordinary
debt was 15 / 35,685 bytes, leaving 113 slots; the remaining 15 are **unknown**,
not verified real customers. Rollback returned 102 / 394,625 bytes. The complete
original 38-job metadata/status digest remained
`a73c4e69915975bee127e1387dd1d345acc40cac75fdf29c44b03dce50902c63`;
no HTTP or mail was invoked. One cold local 87-index preflight took 0.210510 s,
with 0.209626 s between its GET_LOCK and RELEASE_LOCK. This local result is not a
production latency guarantee. The release coordinator must take a fresh complete
backup, review the guarded operation and read back actual current debt before
applying it; this worker never applies it in production.

Deployment must back up database and source before activation, initialize/read
back only through reviewed native code, and record sanitized pool counts/bytes,
old held-job IDs/content hashes/attempts and service state. This worktree writes
only its exclusive local instance; the release coordinator owns production
migration and readback. Rollback restores source/configuration while preserving
all native records/jobs and registry data. Never delete the option or old jobs
to regain capacity. If older code writes during rollback, reconcile those new
native sources under a locked reviewed migration before re-enabling enforcement;
otherwise an existing registry cannot account for writes that bypassed it.

## Acceptance boundaries

Native evidence must cover: real site admission with rotated identities, ordinary
and approved separation, final first-save count/bytes, complete legal large drafts,
two DB workers competing for final slots, provider/SMTP mutex absence, interrupted
first save/callback, exact same-order/job recovery, native approval/reset/PI,
staff promotion rollback, erasure, historical debt and explicit producer exceptions.
EN/DE at 1440 and 390 must prove normal submission, honest full-capacity refusal,
retained fields and product draft, with no additional normal steps. Copy review is
recorded in [copy-review.md](../acceptance/2026-10-22/568/copy-review.md).
Local/CI evidence is not production inbox evidence; real customer delivery after
release remains a distinct authorized readback gate.

The fixed-source review and CI failure recipes, actual native red/green seams
and narrowly scoped fixture corrections are recorded in
[review-repairs.md](../acceptance/2026-10-22/568/review-repairs.md).

## Current protected-base integration and historical evidence

The integration starts from production-tracking `38ef4825` and retains the current
pre-send/native-origin, required proof/Campaign v3, source tombstone/freshness,
product-cache and TLS boundaries. Existing #568 acceptance screenshots and 233-test
records describe its earlier candidate; they are not evidence of this combination
or a new production deployment. Current native evidence and remaining release
gates are recorded in the current-integration acceptance note.

Historical disposition retains the byte-identical, separately approved 87-entry
manifest (SHA256 `451978ea1d1be0901d37e8a4302c00e1cbb973d7092c012b7b348ebc29977eee`),
its recorded snapshot SHA and historical rule. The helper requires that exact
artifact; it does not relabel it to a newer detector. Every current native body,
source and received status must independently match, including the current
campaign detector, before any batch entry runs. Control 8037 remains excluded.
Each entry reloads native core/items/meta, actor capabilities and exact private
note metadata under its actual mutex. An unreadable history page or source is
unknown, not evidence of empty debt or deletion. A verified deletion alone can
release absent-source occupancy. No production disposition is authorized by a
local mechanism test or by these historical aggregates.


## Failed native consumer before its first attempt

A native Action Scheduler single action becomes failed when its callback throws;
keeping a durable job alone does not keep a pending consumer. Only failure in the
Outbox retry's initial hold/transaction reads or native pre-quota witness has a dedicated server-side typed
witness. It proves that no quota reservation or transport was reached. Ordinary
exceptions, later delivery/ACK uncertainty and browser data cannot produce this
recovery authority.

The native failed-execution callback verifies the exact mail hook/group and single
integer job ID. It records a fixed phase on that same existing private, readable,
unheld job, without changing Message, attempts, capacity or budgets. Scheduling the
same job and consuming the phase into its one confirmed successor share a native
transaction. Duplicate/late callbacks cannot advance a different successor.
A scheduling failure retains the unscheduled phase for the existing independent
minute heartbeat. That heartbeat reads only these marked jobs, bounded by the
existing total native mail envelope. It never scans or releases historical held
jobs. An erased/held/missing original is not scheduled.

Pre-attempt recovery uses the existing Outbox RETRY_DELAYS in order, with at most
that sequence's number of successors. Exhaustion retains the original job and a
fixed health diagnostic for staff; it neither refunds debt nor invents a new
message. Once a successor is confirmed, the old phase cannot recover any later
untyped/after-transport failure. Every eventual attempt still passes the current
mandatory send authorization and unchanged host quota.

A confirmation callback's tentative pending result is not final until its own
mutex release and ConnectionFence checks succeed. Failure returns unavailable,
retains the known native locale and never claims an uncommitted job/ACK was saved.


The pre-transport recovery phase is not proof that a different consumer has never
attempted this job. Every real Outbox invocation, including immediate/after-commit
consumers without an Action Scheduler in-progress row, first commits and reads back
an original-job attempt witness under its native row lock. The witness contains
only a native UUID, the complete Message digest and the fixed open/ready state;
its size is constant and bounded per existing queue slot. Logical capacity still
counts the complete encoded Message, including NativeOrigin, without a second
content copy in operational metadata.

An unresolved open witness blocks every later invocation and recovery heartbeat.
Only a quota wait with no IO or the existing definite false result resolves that
exact owner's witness to ready. A confirmed success deletes the original job and
its metadata; privacy erasure clears the Message and operational witnesses.
Unhandled/unknown outcomes retain open, the original job and its charged capacity
and budget. Lock release alone cannot turn them ready. The existing false/retry
contract is retained; this is not a claim of SMTP protocol exactly-once delivery.
