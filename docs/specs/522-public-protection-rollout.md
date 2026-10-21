# Public-entry protection: combined rollout

Owner scope: #505, accepted #507/#508, implementation #511/#516/#519/#520/#521.
This branch combines the reviewed implementations with current main. Production
is a separate state; no local or CI result is described as activation.

## Integration changes

- Inquiry Sender keeps #520 read-only preflight and native stable receipt ID,
  and prepares #511 assessment context before the first order save. All labels
  retain the native received inquiry and normal team notice.
- The actual #511 HTTPX assessment outlet uses #521 AsyncTransport for Jev. A
  depleted or unavailable journal becomes uncertain with a fixed diagnostic.
  The original absolute ten-second deadline still covers async journal waiting,
  retry and body read; cancellation never sends later. Native route/model stay.
- Current-main marketing entry recovery and #521 manual inquiry fallback share
  the existing Hero field snapshot `{text, version}`. An explicit fallback reads
  its current text, including a customer-cleared empty field. It cannot revive an
  older question. Both marketing and inquiry-handoff build entries remain.
- All independent privacy erasure/anonymizer fixtures are retained. EN/DE native
  catalogs are merged with existing translations first and generated assets rebuilt.
- Nightly feed/compatibility rotation must invalidate same-day engineering reuse
  against the actual running service, not a static deployment timestamp. The
  trusted live-version integration is being finalized before activation.

## Activation sequence

1. Complete combined real WordPress, provider/deadline, browser and two-axis
   review; green CI on the combined fixed head. Preserve unrelated main changes.
2. Complete local-only full incremental backup before private configuration/data
   writes. Existing atomic deployment creates an additional DB snapshot and keeps
   the previous code. Back up existing VPS environments, current releases and
   site config privately; no credential appears in repository or logs.
3. Publish service and plugin code with shared admission initially observe. Use
   existing service token, persistent private provider/work journals and actual
   engine cache. Validate authenticated service readback and reject unauthenticated
   expensive private requests without invoking any provider.
4. Install an independent once-per-minute host recovery command alongside native
   due-cron, run/read heartbeat at the next actual scheduled minute, then enable
   the observation-only inquiry assessment. Missing heartbeat keeps immediate
   normal notification with uncertain instead of waiting for a model.
5. Verify the official production Turnstile widget on an interaction in the actual
   target browser/network, without sending an attack or creating test business
   mail. Then enforce scoped verified writes and read the actual modes/health back.
   Browsing stays passive; confirmation faults retain input and offer retry/email.
6. Read back each public native entry, resource gate and model outlet. Record
   actual evidence and network coverage. No region-wide availability assertion.

## Rollback

Public mode off restores native entry behavior. Disable new inquiry assessment
while retaining recovery until pending handoffs drain. Revert service environment
and versioned releases, and atomic site code through rollback-deploy. Do not erase
quotas, real inquiries, staff evidence or historical tables. No DNS or purchase.
