# Inquiry assessment: observation only

Owner confirmation: [10-second window and labels only](https://github.com/AssassinFlash/de-linker/issues/507#issuecomment-6320659705). Implementation: [询盘 Jev 初判标签：后台10秒窗口与正常通知兜底](https://github.com/AssassinFlash/de-linker/issues/511). The owner separately authorized the current Codex to implement this issue despite the earlier Claude Opus staffing rule; no model configuration is changed.

The fixed empirical pilot at commit `9902812a94814e20a537fe1697ae77eb91117720` measured 30 synthetic cases twice, p50 3.993s / p95 5.617s / max 5.902s. It supports feasibility, not production accuracy or delivery latency. The same narrow two-question rubric is versioned `inquiry-observation-v1`.

## Customer boundary

A valid inquiry is stored with its current business snapshot. The customer sees the existing success response and receives the existing receipt without a Jev call in that request. Contact, guest/customer product inquiries and Genie handoffs use the shared Sender and team notification. Classification does not reject, quarantine, delete, change approval or create another customer step. Registration and chat routing are unchanged.

The snapshot contains the validated submission/billing fields, related account approval/VAT, product lines and any associated current owned Genie transcript/readings that are actually retained. It does not fetch a generated summary or raw file, open a new conversation, read arbitrary account history, or include credentials. Context availability and retained scope are explicit. Plain contact has no implicit Genie conversation. Snapshot before the received transition preserves the state before later conversation edits. Missing or rejected material is not claimed to have been read.

## Lifecycle

```text
Sender (no new network I/O)
  save inquiry + immutable snapshot + accepted_at/deadline
  change status -> customer receipt stays on its normal listener
                -> team listener schedules process and expiry
background process
  original remaining budget -> authenticated existing Genie service
  native OpenRouter /api/v1/systemone -> typesafe/jev-1.13
  validate model, schema and classification/basis consistency
  atomically save initial_result and one persistent existing Outbox message
existing Outbox
  sending quota, configured recipients/sender, test rewrite, delivery retries
```

`deadline = accepted_at + 10 seconds`, never renewed by retries. Timestamp is taken immediately before the ordinary inquiry save, making the window conservative by that save's duration. Queueing consumes the same budget; a late-starting worker calls no model. The service uses one absolute asynchronous timeout, including at most one transient retry; WordPress bounds the service call by remaining time. The fixed native endpoint cannot be replaced by a configurable chat endpoint. No alternate model or quality cascade is used.

Worker `started_at` and `queue_seconds` are recorded separately from the service duration and total elapsed time. Normal and suspected spam are advisory labels. Uncertain, conflicting fields, missing credentials, protocol/model errors, service failure and deadline expiry are all explicitly unable to assess. Vendor confidence is not a calibrated production threshold. Stored data separates latest/raw typed choices from the immutable initial_result in the first notice. A late result updates staff evidence and never generates another email.

## Native mechanisms and crash recovery

WooCommerce's order/meta API remains the record authority and supports classic/HPOS. Woo's native Action Scheduler persists background processing/expiry using only an inquiry ID; the full snapshot is not placed in scheduler arguments. LiveCanvas and WindPress remain unchanged because no customer composition or styling changes. Native Woo alone does not provide a versioned model observation, a classification deadline, or a single deferred team-only listener, so a narrow `Inquiry/Assessment` module supplies those missing data/lifecycle functions. It creates no second mail queue or custom inquiry storage.

A connection-owned MySQL advisory mutex, namespaced by database and table prefix like the existing Genie lock, separates classification from notification release. It waits zero seconds and releases on connection death. Notification rendering is captured while Woo's locale and sender filters are active. An InnoDB transaction stores one existing Outbox job and its inquiry notification_job pointer together, reading back both before commit. After a crash, recovery schedules that same job, not another generated email. A competing result retries only its small typed answer, never the model/deadline. Rendering/storage failures remain pending and produce a fixed diagnostic. Existing SMTP transport retries cannot promise exactly-once delivery after an ambiguous external transport failure; the new guarantee is a single logical team message.

Independent once-per-minute recovery uses a real host CLI cron, not the next visitor page hit. It releases expired jobs and repairs a committed notification handoff until the Outbox has delivered or exhausted its normal retry policy. Two missed minute heartbeats (120 seconds) make readiness fail open for new inquiries: no model call, an unable-to-assess label, and the original immediate mail delivery behavior. Missing service configuration takes the same path. A running model process cannot hold the release mutex. The classification wait is ten seconds; scheduling/Outbox quota/SMTP travel are not a ten-second inbox SLA. A stopped scheduler may delay release until the independent recovery tick; health failure is visible rather than described as a successful classification.

Staff can inspect a native Woo meta box and save a separate manual correction protected by capability and record-specific nonce. Raw model evidence stays unchanged; no email, account action or online learning follows a correction. New snapshot/raw staff note fields are emptied by the live-pull anonymizer and operational enable/heartbeat options are omitted from local snapshots.

## Activation and rollback (review/deployment owner)

The feature ships dormant (`linker_inquiry_assessment_enabled=no`). Deploy both service code and WordPress plugin before enabling. This execution task does not merge, deploy or write production.

1. Follow the existing backup/deployment/readback runbook. Confirm the existing authenticated Genie service is healthy and the Jev native key is available there; never copy that key into WP.
2. Install a real once-per-minute host cron alongside the existing due-cron command:

   ```sh
   /usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html linker-commerce inquiry-assessments
   ```

   The scheduler's existing due-cron must also run independently of visitors. The recovery command refreshes the readiness heartbeat and drains expired handoffs; it never calls a model. Do not infer that hPanel cron was configured from a passing local CLI run.
3. Run the recovery command once, verify the heartbeat advances at the next actual scheduled minute, then set `wp option update linker_inquiry_assessment_enabled yes`. Verify service URL/token presence without printing their values and verify the first records/queued message labels by readback. No production attack/email test is authorized by this spec.
4. Rollback: `wp option update linker_inquiry_assessment_enabled no` stops new model classification. Keep plugin recovery and its CLI cron until existing assessment handoffs are released; expired pending jobs still notify as unable to assess. Retain evidence/override fields; no destructive migration or table deletion. Revert code only after pending jobs are drained; remove the added cron after drain if reverting the module.

## Verification

Real local instance `g511`, port 9210, dedicated worktree `codex/511-inquiry-jev-labels`, snapshot `20261022-0018` (taken 2026-10-22 00:21 Asia/Shanghai). Evidence is saved under `docs/acceptance/2026-10-22/511/`.

Fixtures cover typed model/protocol failures, strict async deadline and retry; real Woo submit with zero classifier calls, normal/spam/uncertain/conflict notices, initial-vs-late result, recovery and idempotent message generation. The real-Woo suite also covers ownership/full retained reading snapshots, unrelated account-history exclusion, worker loss/concurrent release and failed message-meta write recovery. Computer Use covers staff correction and native email renderings EN/DE at 390/1440; the acceptance report records customer form/success comparison and its exact limits. Report incomplete evidence explicitly; do not infer deployment or production email delivery from local queue assertions.
