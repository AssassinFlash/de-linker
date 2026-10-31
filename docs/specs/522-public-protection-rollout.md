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
- Nightly feed/compatibility rotation invalidates same-day reuse through the
  private authenticated `/resource/version` readback. The digest uses the same
  bytes that constructed the running engine; disk changes alone cannot pretend
  an old worker loaded new data. Expected and response version headers prevent
  a restart between read and compute from storing a different worker's result.
- Every nonempty receipt suppression reason yields receipt=false and the existing
  no-confirmation notice. Fixed provider budget diagnostics survive the PHP
  boundary. Same-origin empty fallback text clears any older tab handoff.

## Activation sequence

1. Complete combined real WordPress, provider/deadline, browser and two-axis
   review; green CI on the combined fixed head. Preserve unrelated main changes.
2. Complete local-only full incremental backup before private configuration/data
   writes. Existing atomic deployment creates an additional DB snapshot and keeps
   the previous code. Back up existing VPS environments, current releases and
   site config privately; no credential appears in repository or logs.
3. Publish service code first with existing environment, then plugin code with
   admission observe. Only after the new native headers are present, enable the
   private provider/actual-work/engine guards using the existing service token,
   persistent private journals and actual engine cache. This ordering avoids
   rejecting the preceding site's calls during the deployment interval. Validate
   authenticated readback and reject unauthenticated expensive private requests
   without invoking any provider.
4. Install an independent once-per-minute recovery execution, run/read heartbeat
   at the next actual scheduled minute, then enable
   the observation-only inquiry assessment. Missing heartbeat keeps immediate
   normal notification with uncertain instead of waiting for a model.
5. Verify the official production Turnstile widget on an interaction in the actual
   target browser/network, without sending an attack or creating test business
   mail. Then enforce scoped verified writes and read the actual modes/health back.
   Browsing stays passive; confirmation faults retain input and offer retry/email.
6. Read back each public native entry, resource gate and model outlet. Record
   actual evidence and network coverage. No region-wide availability assertion.

## Independent scheduler on this host

Use one independent driver for WordPress's native due events, including
`linker_inquiry_assessment_recover` at its owner-approved 60-second interval.
Page visits are not the driver. Hostinger's control-panel cron is the authority:
actual panel readback on 2026-10-31 confirmed this once-per-minute command:

```sh
/usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html cron event run --due-now --quiet
```

The earlier absence of a shared-host `crontab` binary and unavailable account
access did not establish that Hostinger could not configure cron. The same
readback found the VPS `linker-wordpress-cron.timer` enabled and active, with a
successful HTTP tick at 12:28 UTC; that duplicate driver must be retired after
confirming natural Hostinger progress. Actual driver retirement and readbacks
belong in the existing acceptance INDEX, separately from this source guidance.

Before switching, record the site's recovery heartbeat using the read-only
command below, then verify it advances at the next natural scheduled minute
without a manual cron invocation. `Queue::recover()` writes that heartbeat
before scanning pending handoffs: it proves callback entry, not scan completion
or completion of all due cron work. Also verify the next scheduled recovery
event advances, the host cron invocation exits successfully, and relevant Action
Scheduler pending/failed work progresses without accumulating new failures.
Inspect those results together; a successful HTTP request alone does not prove
the callback ran, and a fresh heartbeat alone does not prove recovery completed.

```sh
/usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html option get linker_inquiry_assessment_recovery
```

Once the Hostinger driver is verified, retire only the duplicate VPS timer:

```sh
sudo systemctl disable --now linker-wordpress-cron.timer
systemctl is-enabled linker-wordpress-cron.timer
systemctl is-active linker-wordpress-cron.timer
systemctl show linker-wordpress-cron.service -p ActiveState -p MainPID -p Result
```

The expected timer states are disabled/inactive; those `is-*` queries return
nonzero for the expected state. Let any already-running bounded service finish
and read back that it has no remaining process. Keep the native WordPress event
and the Hostinger panel command in place, then verify another natural heartbeat
advance with only that driver enabled.

The reviewed VPS HTTP timer is an explicit fallback only when host-native CLI
scheduling is unavailable. It requests the existing public `wp-cron.php`; its
55-second curl timeout and 60-second systemd bound prevent timer-process buildup.
It adds no credential or API permission. To restore this fallback, explicitly
run `sudo systemctl enable --now linker-wordpress-cron.timer`, inspect
`journalctl -u linker-wordpress-cron.service --since "5 minutes ago"`, and verify
natural heartbeat progress. Disable the unavailable Hostinger panel job as part
of that handoff so it cannot later resume as a duplicate driver. Native cron
locking is overlap protection, not permission to leave both drivers scheduled.

To return from fallback, restore the exact once-per-minute Hostinger panel
command above, verify its natural progress, disable the VPS timer with the
commands above, and confirm progress again. A bounded transition/readback is
operator-controlled; there is no automatic parallel fallback. During rollback,
retain the selected independent driver and native recovery event until pending
handoffs drain. Missing heartbeat keeps normal immediate notification with an
uncertain assessment rather than waiting for a model.

## Rollback

Public mode off restores native entry behavior. Disable new inquiry assessment
while retaining recovery until pending handoffs drain. Revert service environment
and versioned releases, and atomic site code through rollback-deploy. Do not erase
quotas, real inquiries, staff evidence or historical tables. No DNS or purchase.
