# Native critical notification reservation contract (#568)

`Linker\Commerce\Mail\Capacity` is the single server-only interface used by
registration (#569), approval, reset and the last native Outbox writer. There is
no browser route, bearer header, model label or customer field that grants it.

```php
Capacity::reserve_critical(string $native_operation, int $count, int $max_bytes_per_message): array|WP_Error;
Capacity::within(array|string $reservation, callable $native_send): mixed;
Capacity::cancel_before_side_effect(array|string $reservation): bool;
```

The caller supplies a stable native operation key. The store retains its HMAC,
never the raw key, recipient, body, reset credential or company information.
Success is `['key' => string, 'remaining' => int]`; failure is a `WP_Error` with
code `linker_mail_capacity`. A repeat with exactly the original count and byte
bound returns the same remaining count. Changing either bound is refused.

Use one count-1 reservation for each independently optional notice. In
particular, registration's team notice and existing customer acknowledgement
must have different native operation suffixes. Their configured lifecycle and
receipt policy remain unchanged. A caller must durably remember a completed or
explicitly skipped notice so a later trigger cannot reopen it.

`max_bytes_per_message` is a proven bound on the **complete** JSON encoding of
`Message::to_array()` as written by JobStore: recipients, subject, body,
resolved headers, attachment paths, critical flag and category. It is not a
limit on raw customer input, PDF file size, physical database pages or SMTP
wire bytes. Native producers must render the actual configured template and
locale, include their legal field bounds and native filters, and test the
result. Unknown template bounds cannot be asserted from a small sample.

`within` wraps only the actual native mail producer. It restores the previous
scope in `finally`, including nested calls and failures. `Producer::priority`
recognizes that trusted scope. JobStore atomically replaces a remaining
critical slot and its reserved bytes with the actual native job's complete
encoded bytes. An oversized or repeated consumed message does not get another
job. Ordinary queue exhaustion does not consume the critical reserve.

`cancel_before_side_effect` accepts only an entirely unconsumed reservation.
The caller must have proved that this **mail operation** did not happen: for
example, native configuration explicitly disabled this optional notice, or
the existing receipt policy explicitly skipped it and the caller durably
records that skip. An account may already exist in that case. This does not
refund account admission or business throughput. A partly consumed, dispatched,
failed, ambiguous or possibly committed mail operation cannot be cancelled.
There is no timer refund for pending reservations or held/failed jobs.

Completed reservation receipts retain the native admission retry horizon of
24 hours. Only their zero-remaining metadata can later be pruned. An additional
256-receipt registry envelope bounds this metadata; it is an operational
allocation, not a customer-demand statistic. Pending reservations remain
charged until actual consumption or the above explicit unused cancellation.

## Last native writer and transactions

Owner-approved initial operating pools are ordinary **192 jobs / 48 MiB** and
critical **64 jobs / 16 MiB**. These are adjustable operating choices. The
256 KiB-per-slot arithmetic behind the aggregate byte envelopes is **not** a
per-message cut-off. A larger complete valid message can use available pool
bytes. Existing private, failed and held jobs are imported as debt without
rewriting, deleting or sending them; historical excess blocks new affected
jobs. Attachment paths are included in message bytes; attachment file storage
is governed by the separate native upload/document boundaries.

The same IntakeStore connection mutex and cache-free option CAS protect count,
byte and reservation decisions. JobStore writes a native private job, reads
back its full message and source association, and acknowledges any durable
source in the same database transaction. Only an actual positive verified job
id is accepted. A full queue or failed readback causes `wp_mail` to return
false, records one fixed-size private health result, and never schedules job
zero or consumes a transport attempt. It does not create an overflow queue.

For ordinary calls outside a transaction, Outbox still attempts synchronous
delivery after durable handoff. The original job is retained for throttled,
failed or unknown attempts and deleted only after confirmed success.

The unique native Action Scheduler recovery action belongs to the same JobStore
owner transaction as original job, capacity and source ACK. It is not added only
after commit: a killed producer between commit and immediate delivery must leave
the original committed consumer. Only successful deletion of that original job
cancels its own pending action. Held historical jobs are not armed by import.

If the native producer already has an outer transaction, job, capacity and AS
action join it; transport is deferred to an independent committed reader.
Rolling back the outer transaction must remove job, AS action and capacity
change with **zero transport**. No inner helper may commit the caller's
transaction. The local MySQL 8 server does not expose `@@in_transaction`, so
transaction detection uses a uniquely named SAVEPOINT/RELEASE probe that
does not commit an existing transaction. Two-connection native tests verify
visibility and rollback, not merely a mocked transaction variable.

`NativeTransaction` and `ConnectionFence` retain the original mysqli client,
native thread identity, strict error mode and zero reconnect retries for short
DB-only writer scopes. WordPress's ordinary reconnect-and-replay behavior cannot
be used inside them: a successful query on a new autocommit client would not
preserve atomicity. Cross-hook native reset/registration consumers may retain a
scope until their final native writer; joined scopes use their own savepoint and
never commit the caller. Paid summary/VIES/provider HTTP and SMTP are outside the
shared site mutex. Transport runs only after a confirmed owned commit, or through
the original AS consumer when a caller-owned transaction must commit separately.
Native KILL, two-client visibility, outer rollback, unknown commit and producer
SIGKILL tests prove the real writer boundary.

## Recovery responsibilities

- Inquiry assessment already owns a durable `PENDING=yes` order and frozen
  snapshot. A full JobStore must leave it pending and its independent recovery
  must eventually create one original job, without running another model.
- Registration owns its user/operation/notice associations and explicit
  optional skips in #569; it consumes this interface instead of adding another
  queue or assuming that a created account means mail was accepted.
- Approval reserves the actual rendered message before approval/session
  mutations and hands off that immutable message on the native state event.
- Reset reserves before native key mutation. Core and Woo retain their native
  key generation and email consumers; the 20-character alphanumeric native
  key shape has equal encoded size in native reset URLs. Native tests compare
  preview and actual messages and protect the previous key on full capacity.
  A short original-client transaction begins at the native generated-key hook,
  before key persistence. Exact server reservation, key mutation, original job
  and AS commit together. A false Woo handoff cannot follow its otherwise
  unconditional success redirect: it returns to the native lost-password form
  with the reviewed unavailable notice and only the username/email retained.
- Proforma notices use an explicit durable pending marker on their native
  issued order/PDF source. The job and accepted-number marker commit together.
  The existing independent minute recovery retries pending source handoffs,
  without treating a status change alone as successful notification.
- Core payment-gateway-enabled notification is already post-write and has no
  reliable original-event rebuild source. Capacity refusal is explicit false
  plus the bounded health record; it is **not automatically reconstructible**.
  This exception is reported in acceptance, not presented as recovered.

Rollback preserves every native inquiry/job and the private capacity option.
Never delete the registry to regain slots or replay historical held jobs.
Restore source/configuration from the reviewed backup and reconcile any
native writes made by older code before re-enabling enforcement. Deployment,
backup, migration/readback and real inbox evidence belong to the coordinating
release task; this implementation worktree does not write production.

Current native substrate tests are `MailCapacityTest`: native last-writer
ordinary exhaustion with critical headroom, explicit full-Outbox false with
zero transport budget, exact reservation consumption/cancellation, and a
second database connection proving uncommitted invisibility plus rollback of
the actual Outbox job/action/capacity. Full #568 acceptance also requires
concurrent final-slot writers, byte boundaries, staff promotion, all five
doors, restore/erasure, and EN/DE desktop/mobile input preservation.
