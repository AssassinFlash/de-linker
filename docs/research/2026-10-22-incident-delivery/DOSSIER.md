# Public-entry incident: notification delivery, capacity and classification scheduling

- Research ticket: [#535](https://github.com/AssassinFlash/de-linker/issues/535); parent investigation: [#533](https://github.com/AssassinFlash/de-linker/issues/533).
- Research scope: delivery/capacity and background assessment forensics only. Other public-entry/security investigation belongs to the parent research.
- Source baseline: `dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0`.
- Native production read-only observations: **2026-10-22 06:44:22 UTC** and **06:47:48 UTC**. All times below are UTC; add eight hours for the owner's local time.
- No production writes, sending, model invocation, mailbox read-state changes, source implementation changes, deployment or PR were performed by this research task. Repository change is this sanitized report only.

## Finding

The attack is exhausting a shared notification budget. At 06:44:22 the application recorded **80/80 sends in its rolling 24-hour window**, with **38 unsent internal inquiry notifications** saved privately. The oldest had waited **27 minutes 20 seconds**. Every one of those 38 pending notices was independently joined to an inquiry and matched the narrowly defined observed campaign; this conclusion does not depend on Jev's label. Only **one** application mail slot becomes available at **07:00:06**; the next old entry expires at **12:08:19**. Letting the queue drain indiscriminately can spend that one opening on the campaign and delay a real customer's notice for hours. [E1, E2]

The initial classification deadline misses are primarily queue-start misses in this sample: **52/88** initial notifications had reason `deadline`, and every one had recorded `queue_seconds >= 10` with **no model duration recorded**. The successfully classified records recorded model durations of **0.122–0.341 seconds**. The live native Action Scheduler dispatcher has a **60-second shutdown-dispatch lock**, and the independent recovery timer runs once per minute. That combination cannot provide a ten-second classification service objective reliably. This is evidence about these records and the observed dispatch mechanism, not a general model-latency claim. [E1, E2, S5–S7]

## Measured production state

| Measure | 06:44:22 / 06:47:48 observation | Meaning and limit |
|---|---:|---|
| Inquiries accepted since 05:45 | 88 | All remain native `inquiry-received`; includes controlled acceptance record #8037. |
| Campaign predicate matches | 87/88 | Predicate described below; remaining record is #8037. Not a population false-positive estimate. |
| First-notification labels | 35 suspected spam, 52 undetermined, 1 normal | These are immutable initial labels, not human truth or necessarily latest result. |
| Pending mail jobs | 38 | All private, all explicit internal inquiry notices, zero failed transport attempts so far. |
| Pending notices matching campaign | 38/38 | Native inquiry-to-job join plus full-message/host predicate, independently checked. |
| Oldest pending notice | 06:17:02; age 1,640 s | App-side queue age, not an inbox delivery timestamp. |
| Mail budget | 80/80 rolling 24h | Includes all mail types; not all 80 can be attributed to this campaign. |
| Pending AS delivery actions | 38 | All scheduled at 07:00:06; the queue is retained rather than discarded. |
| Next two ledger expirations | 07:00:06, 12:08:19 | Only one new opening is created at the first timestamp, absent a route/capacity change. |
| Configured internal SMTP | Authenticated configuration valid | Configuration/identity check only. |
| Last SMTP outcome | Success at 06:16:06 | SMTP accepted the last recorded attempt; not an inbox proof for every notice. |
| SMTP fallback warnings today | 0 in current `linker-mail` daily log | The observed internal path is authenticated SMTP, not an assumed PHP-mail-only transport. |
| Latest accepted inquiry in snapshot | 06:37:57.669249 | Precedes root's 06:38 containment; this snapshot found no later accepted record. Does not prove all hostile requests stopped. |
| Initial-deadline queue delay | 10.283–60.597 s for 52 records | Every initial deadline record started too late for the absolute budget. |
| Successful model duration | 0.121984–0.341207 s | Provider-reported model timing, not submission latency or full round trip. |
| Recovery heartbeat | 06:44:03.6448 | Recovery active at snapshot; it does not guarantee ten-second startup. |

The earlier 06:34:15 sample had 80 inquiries, 30 queued notices, 47 deadline labels, 32 suspected-spam labels and one normal controlled test. Of those 80 records, 70 had their optional customer acknowledgement skipped for `daily_cap`, nine had no skip marker and one was the one-mail controlled acceptance exception. A skipped acknowledgement does **not** mean the inquiry or internal team notification was rejected. At 06:44 the count had grown to 88 inquiries and 38 queued team notices. These are different timestamped denominators. [E0, E1]

### Exact campaign membership used for the hold recommendation

The full stored message must match this anchored pattern, and **every parsed URL must have hostname exactly `fredmer.buzz`**:

```text
\AВам перевод\s+\d+\s+руб\.\s+(?:получить|забрать)\s+тут\s+https?://\S+\s*\z
```

URLs are treated as untrusted strings; none were opened or resolved. The predicate is intentionally narrower than a language, nationality, IP range, free-mail domain, or a general Jev spam label. The amounts/tokens vary, so an exact raw-message hash alone does not identify this campaign. Hashes are retained privately for integrity and rollback readback. A different message must remain outside this campaign action until independently evaluated. [E0, E2]

## Delivery implementation and actual transport

1. All `wp_mail()` messages enter `Outbox::intercept()`. `Outbox::attempt()` checks one `Throttle` before choosing SMTP or PHP mail. The configured limit is **8/minute and 80/rolling24h**, shared by internal notices, customer receipts, authentication/account mail and digests. There is no priority reserve or campaign aggregation in this source. Do not infer a vendor mailbox's current paid capacity from those source comments. [S1, S2]
2. On quota exhaustion, Outbox creates/keeps a private job and schedules the next slot without incrementing the transport-failure count. Thus `failed_count=0` can coexist with long delivery delay and a full budget. `wp_mail()` interception also returns success when a message is queued; submission success is not receiving-side delivery proof. [S1, S3]
3. Internal headers persist an explicit internal marker. `InternalSmtp` reads credentials from a private file, verifies the sender identity, configures authenticated SMTP for internal mail, and resets the reusable mailer afterwards. Outbox falls back to PHP mail only after a selected SMTP attempt fails, with a fixed warning. The observed valid configuration, last native SMTP success and zero current daily fallback warnings support SMTP being active here. Neither SMTP acceptance nor a deleted successful job proves every receiving mailbox accepted the message. [E1, E2, S1, S4]
4. Successful jobs are deleted; final failed jobs remain draft. The current 38 private jobs have zero attempts because they are waiting for quota, not because 38 SMTP attempts failed. [E1, S1, S3]
5. Throttle records an application attempt before transport. An internal SMTP attempt followed by PHP fallback shares that one recorded application slot. `get_option`/`update_option` counting has no atomic reservation in this class. Raising global worker concurrency without first addressing reservation can race the cap; this is a code risk, not a demonstrated explanation of today's 80-count snapshot. [S1, S2]

### The expired forwarding destination is a separate problem

The controlled record #8037 previously reached the primary `sales@sunriverinverter.com` inbox (UID 1365). An additional forwarding expansion to `sales@sunriver-electric.com` bounced (UID 1366; later downstream retry/bounce evidence is separately held by root). The owner now states SunRiver Electric is expired and will not be renewed. Retire that forwarding destination; do not treat its failure as proof that the website rejected #8037 or that the primary inbox did not receive it. Verify the owner's retained internal To/Bcc route separately before changing recipients. No forwarding or recipient setting was changed by this research. [E3, owner 2026-10-22]

## Why the ten-second classification window is missed

`Queue::prepare()` records an absolute `accepted_at + 10s` deadline before the ordinary save. `defer()` schedules one async PROCESS action plus an EXPIRE action. PROCESS refuses to call the model after that deadline; queue delay explicitly consumes the budget. FINISH preserves the first-notification result and records late results separately without a second notice. Recovery scans the native pending records once a minute and releases them without calling a model when expired. This protects the customer from waiting but cannot make slow dispatch start earlier. [S5, S6]

Live `ActionScheduler_QueueRunner.php` SHA-256 is `0b5bdaf8a7fdb406edc1ac1eb93855dd483478e64278be9302cbfe5284f4e5e1`; it exactly matches the local saved WooCommerce package source examined here. Its shutdown dispatcher only starts an async queue at most once every 60 seconds. The async worker chains only while due work exists. An inquiry arriving during the lock after a worker has drained can therefore wait for the minute cron runner. Native action logs show both paths: #8201 PROCESS ran via Async Request shortly after enqueue, while #8197/#8198 PROCESS started via WP Cron tens of seconds after acceptance. All 52 deadline records had `queue_seconds >= 10`, with no provider timing. This makes dispatch delay a directly observed cause for those records. It does not identify every possible cause of an async request not launching. [E1, E2, S7]

The timer's 55-second HTTP timeout / 60-second systemd bound prevents its caller from piling up processes; it is not an assessment-start SLO and should not be described as one. [S6]

## Immediate reversible notification containment

This is a recommended native-data procedure for the parent operator, **not a claim that this research executed a hold**. The parent must back up before mutation and attach post-change readback to the incident record.

### Preserve records and isolate only confirmed campaign notifications

- Keep all native inquiries and all 38 original private mail jobs, their message bytes, recipients, attachment references, attempt counters and initial classification evidence.
- Preserve a private manifest: inquiry ID, job ID, message SHA-256, prior pending value, job status, exact AS hook/args/group/due time, campaign predicate revision, hold timestamp/reason and operator. Avoid raw PII in the repository report.
- Mark only matched native inquiries with an incident hold reason and set their assessment pending marker to a distinct `held` value. Keep jobs private; do not turn them into final transport failures or delete them.
- Cancel the exact pending `Outbox::HOOK([job_id])`, PROCESS `[inquiry_id]`, EXPIRE `[inquiry_id]` and any FINISH action whose first argument is that exact inquiry. Use native Action Scheduler APIs and exact arguments/group; do not cancel the entire `linker-commerce` group, unrelated mail, registration, login or password recovery.
- FINISH can contain two arguments; discover and preserve the exact action args instead of assuming `[id]` is sufficient.

### Race boundary that must be verified

There is **no existing durable hold guard in Outbox**. Arbitrary `_linker_incident_hold` metadata does not stop `Outbox::retry()`, which loads a job and attempts it. Similarly, `Queue::expire()`/`dispatch()` does not inspect the pending marker before re-enqueueing a known existing job. A recovery iteration that selected an order before `pending=held` can still recreate its mail action. Marking held alone is insufficient. [S1, S5]

The currently known actions are all future-scheduled for 07:00:06, leaving a bounded containment opportunity before the next mail slot. For data-only containment:

1. Write/read back the scoped hold markers before canceling native actions.
2. Cancel exact pending actions and inspect **both pending and in-progress** matching actions.
3. Repeat the exact-action cleanup after the next actual minute-recovery tick; verify no matched action is in progress and no new matched pending action exists. Do this again before 07:00:06 if needed. A new recovery scan no longer selects `held` inquiries.
4. Retain a readback showing unchanged inquiry/job counts and message hashes, all matched native jobs still private, all unrelated jobs untouched, and zero pending/in-progress actions for the held set.
5. Continue observing held count and scheduled-action drift until a proper source-level hold check ships. The data-only method is not protection against a later manual `Outbox::retry()` or deliberate re-enqueue.

If a matched callback is already in progress, native unscheduling does not recall its executing PHP. Do not claim cancellation or safe containment from canceled-action rows alone. Recheck its outcome and the throttle before continuing. [S1, S5, S7]

### Release and rollback

Releasing a falsely held real inquiry must restore the existing job rather than construct another one. Recheck the native inquiry and job hash, leave all message routing intact, clear the incident hold, restore pending to `yes`, and schedule exactly one Outbox action at a permitted future slot. Read back the scheduler and retain the audit trail. Race tests must prove that recovery and manual release do not create duplicate delivery attempts. Do not erase the throttle ledger, artificially backdate sends, bypass the vendor cap, mark held mail sent, or replay every held campaign item as a batch. The long-term implementation needs a native job hold/priority state enforced **inside retry/dispatch**, with an owner-visible held count and a one-click release preserving the original job. [S1–S3, S5]

## Recommended permanent changes, ordered by evidence

| Priority | Change | Reason / acceptance evidence |
|---|---|---|
| P0 | Confirmed-campaign notification hold and aggregation, retaining every saved inquiry | Stops this known campaign spending the next scarce slot. One bounded incident summary can link to retained records; automatic content deletion is unnecessary. Prove exact predicate isolation, native hash retention, held-state visibility and duplicate-free release. |
| P0 | Mail budget headroom and priority by message purpose | Separate normal/undetermined genuine-candidate notices and authentication from confirmed-campaign bulk. A global cap still applies; a local priority does not create provider capacity. Establish route-specific actual provider limits/account status before any increase. |
| P0 | Retire the expired forwarding expansion | Removes a known dead destination and repeated bounces; preserve the currently authorized primary/Bcc route. Prove with settings readback and the next normal authorized business message, not multiple test sends. |
| P1 | Deadline-aware independent assessment dispatch | Keep the absolute 10s window and customer response independence. Use a narrowly scoped native AS worker driven more frequently than once a minute; current AS CLI supports exact `--hooks` filtering. Isolate PROCESS/EXPIRE/FINISH from mail drainage, bound runtime/batches, prevent overlapping workers, and measure actual PHP/SSH startup cost. Do not add `--force` or raise global concurrency as a shortcut. |
| P1 | Durable priority/hold enforcement in native Outbox | Native record and job are retained. `retry`, recovery and manual retries all honor held state. Tests cover held-before-callback, concurrent recovery/release, SMTP failure, quota waits and late model results. |
| P1 | Delivery-health view independent of the mail path | Show saved/held/queued/sent/failed separately; include oldest queue age, next slot and remaining rolling budget. A warning sent through an already exhausted mail queue cannot be the only alert. |
| P2 | Human-reviewed false-positive and recovery samples | A Jev label remains advisory; undetermined or model-unavailable submissions keep their record and ordinary team route. Measure accidental hold rate and time to release against human-reviewed examples. Do not calculate model accuracy from its own labels. |

Worker scheduling acceptance must use real queue-start latency under normal and burst load, not merely a green heartbeat. A provisional objective is at least 95% of accepted submissions obtaining a valid **first** label inside the existing ten-second window, with bounded fallback and zero customer model wait. That percentage is a proposed engineering target, not a measured current guarantee. A more frequent polling interval is not itself sufficient: boot cost, AS claims and real request behavior must be measured. [E1, S5–S7]

Mail capacity policy must be derived after obtaining actual route/account limits and expected legitimate peak volume. The current observed 80/day cannot simultaneously guarantee instant notification during an attack and continue sending one email per hostile submission. The choice is controlled aggregation/hold plus priority, or greater verified transport capacity; raising a numeric constant without verifying the physical route is not a complete solution. [E1, S1, S2, S4]

## Evidence and reproducibility

Private evidence is stored locally outside the repository. These files contain no credentials; the original E0 snapshot contains submitted content and remains private.

- **E0** `/Users/chesterjohn/de-linker-data/incident-20261022/recent-runtime-sample.json`: 06:34:15 native sample supplied to this research. Counts were recomputed, not inferred from email volume.
- **E1** `/Users/chesterjohn/de-linker-data/incident-20261022/delivery-runtime.json`: 06:44:22 native `wc_get_orders`, `JobStore`, `Throttle`, `SmtpOutcome`, heartbeat and read-only AS tables/log readback. It contains only IDs, timestamps and categories for delivery analysis.
- **E2** `/Users/chesterjohn/de-linker-data/incident-20261022/delivery-campaign.json`: 06:47:48 native inquiry/job join, exact campaign predicate booleans and message hashes; source hash and fallback-log count. No message bodies, recipient addresses or secrets were exported.
- **E3** `/Users/chesterjohn/de-linker-data/acceptance-522-availability-20261022/`: previous authorized #8037 physical acceptance and expired-forward bounce evidence; not a new mail test in this research.

Frozen project primary sources, all at baseline `dcd5560d`:

- **S1** [Mail/Outbox.php](../../../plugins/linker-commerce/includes/Mail/Outbox.php): interception, quota waits, SMTP/fallback, retry and successful-job deletion.
- **S2** [Mail/Throttle.php](../../../plugins/linker-commerce/includes/Mail/Throttle.php): rolling 8/80 application budget and next-slot calculation.
- **S3** [Mail/JobStore.php](../../../plugins/linker-commerce/includes/Mail/JobStore.php): private native jobs, failure state and persistence.
- **S4** [Mail/InternalSmtp.php](../../../plugins/linker-commerce/includes/Mail/InternalSmtp.php), [Mail/SmtpOutcome.php](../../../plugins/linker-commerce/includes/Mail/SmtpOutcome.php) and [Mail/Message.php](../../../plugins/linker-commerce/includes/Mail/Message.php): private transport configuration, fixed outcome diagnostics and internal routing marker.
- **S5** [Inquiry/Assessment/Queue.php](../../../plugins/linker-commerce/includes/Inquiry/Assessment/Queue.php), [Client.php](../../../plugins/linker-commerce/includes/Inquiry/Assessment/Client.php), [RecoverySchedule.php](../../../plugins/linker-commerce/includes/Inquiry/Assessment/RecoverySchedule.php), [Sender.php](../../../plugins/linker-commerce/includes/Inquiry/Sender.php) and [ReceiptBudget.php](../../../plugins/linker-commerce/includes/Protection/ReceiptBudget.php): acceptance deadline, classification lifecycle, recovery and independent optional receipt limits.
- **S6** [linker-wordpress-cron.timer](../../../services/genie/ops/linker-wordpress-cron.timer), [service](../../../services/genie/ops/linker-wordpress-cron.service) and [rollout spec](../../specs/522-public-protection-rollout.md): actual independent minute runner design and timeout bounds.
- **S7** Saved first-party WooCommerce package at `/Users/chesterjohn/de-linker-data/20261021-1023/live/plugins/woocommerce/packages/action-scheduler/classes/ActionScheduler_QueueRunner.php`, `ActionScheduler_AsyncRequest_QueueRunner.php`, and `WP_CLI/ActionScheduler_WPCLI_Scheduler_command.php`; live QueueRunner SHA-256 verified equal in E2. Source shows 60s dispatch lock, native chaining, bounded claims and hooks-filtered CLI. No external secondary source was used.
