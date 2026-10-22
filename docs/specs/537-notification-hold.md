# Retained notification holds and staff release

Issue [#537](https://github.com/AssassinFlash/de-linker/issues/537), incident [#533](https://github.com/AssassinFlash/de-linker/issues/533). Release base is production commit `dcd5560d`; this change does not include the unrelated product-selection update on main.

## Contract

A server-side `_linker_incident_hold` marker on an inquiry or its notification, or an inquiry pending marker `held`, pauses the original team notification. It does not reject the inquiry, alter customer/account status, change its Jev label, delete a mail job, mark delivery successful or mark a final transport failure. Jev labels never create a hold.

Existing incident records remain compatible: order and job hold arrays contain incident, timestamp, reason, manifest hash and their native IDs; the inquiry keeps its existing `notification_job`. New assessment jobs persist `_linker_mail_inquiry`; legacy incident jobs recover this association from their job hold marker. Release persists the association before removing legacy markers. No destructive migration or global data rewrite is needed.

## Guarded lifecycle and race boundary

- `Outbox::retry` resolves the native inquiry, acquires the existing connection-owned `release-{inquiry}` mutex, refreshes job metadata, checks the hold and reloads the original job before any throttle recording or transport call. A busy held job does not enqueue another retry.
- Queue PROCESS retains the process-spend mutex and also holds the release mutex across its fresh hold check, provider call and notification handoff. FINISH, EXPIRE and dispatch return while held. FINISH also checks the hold before scheduling a result after a busy release lock. Recovery skips the ordinary `held` selection and its expiry callback independently checks the hold for stale or order-marker-only selections.
- Order evidence uses Woo's `read_meta_data(true)`; per-job core metadata cache is invalidated at guard boundaries so another DB connection's release cannot remain invisible in request-local cache.
- A writer establishing a hold must acquire the same `release-{inquiry}` mutex and persist both order/job markers. A callback that already owns this mutex may finish its already-started I/O before a new hold can be established; no claim is made to recall an SMTP message or provider request already in flight. Once the hold is established under that boundary, retry/model/handoff callbacks do no further mail/model work for it.
- The existing ten-second absolute assessment deadline, customer submission behavior, native validation, admission verification, quotas, model routing and mail recipients remain unchanged.

## Native staff interface

The existing inquiry review box shows notification hold reason, UTC timestamp and original job ID. It states that the inquiry and original notification remain retained. The release control uses a separate footer form, avoiding a nested Woo editor form, in both classic and HPOS edit screens.

The controller requires a record/reference-bound nonce. The release service independently requires `manage_woocommerce`. It rechecks the exact hold reference, original private internal job and source association under the release mutex. It refuses an in-progress delivery action or stale reference.

Release uses the original job and its unchanged message, headers, attachments and attempts. It writes a private order-note audit with actor, timestamp, reference and previous hold, removes hold markers, restores pending `yes` and schedules one future attempt through the real throttle. It performs no inline transport. A repeated release with the same reference returns the persisted release audit and creates no second event or logical message. A native transaction and readback cover the audit, metadata and schedule; failed scheduling leaves the original hold and message intact.

The UI says **Released for delivery**, which describes queueing, not an inbox receipt. Capturing a message previously made Woo's native email logger write an incorrect “sent” note. The capture now temporarily uses Woo's native `woocommerce_email_log_enabled` filter for that exact email object, so assembly produces neither a false sent log nor a failed-delivery log. Other emails and Outbox transport logging remain active. Historical notes are retained.

## Verification and rollback

Native integration covers manual retry, all stale assessment callbacks, a hold before classification, order-only/pending-only source-bound holds, capability and cross-record/missing nonce rejection, two actual PHP/DB connections, a busy mutex, concurrent and repeated release, one eventual delivery from the original job, failed-schedule rollback and capture without a false delivery note. The CI native assessment step includes this class. Local delivery stays isolated to the tester.

EN and formal DE staff copy is compiled from the PO catalog. Computer Use checks held/released states at 1440 and 390; evidence and actual native readback are in `docs/acceptance/2026-10-22/537/`.

There is no schema deletion or record replacement. Reverting this code restores the previous unguarded retry behavior, so a rollback must first preserve the incident manifest, cancel only held jobs' exact actions and retain data containment/reconciliation until the durable guard is restored. Do not deploy the old code while relying on hold metadata alone. Do not erase or backdate the throttle ledger, mass-release campaign notifications, or represent held/queued mail as received.
