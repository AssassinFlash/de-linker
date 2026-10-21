# Inquiry assessment acceptance

Dedicated worktree `codex/511-inquiry-jev-labels`, base `67e0d589`, local instance `g511` at port 9210. Production snapshot `20261022-0018` was loaded before UI work. All writes and email fixtures in this acceptance were local; no production inquiry was submitted and no external test email was sent.

## Execution evidence

- `just check`: PASS (PHP/JS/Python static checks, catalog validity/coverage and source/build parity).
- `LINKER_WP_ROOT=…/g511/wordpress just test`: PASS. Genie 1915 passed / 1 skipped / 195 deselected / 6 expected failures; plugin unit/JS suites, engine, local/pull/cutover and existing package browser fixtures passed. Logs are summarized in `checks.txt`.
- Commerce real-Woo `InquiryAssessmentTest`: 11 tests / 121 assertions PASS, including zero classifier calls during Sender, every label notifying, immutable first notice/late result, expired/no-traffic recovery, missing heartbeat, full retained owned context, no account-history fallback, partial email-meta write failure rollback/recovery, and two independent PHP workers plus connection death. Worker memory matches the integration suite (2 GiB); its original 128 MiB default exhausted memory loading the full Woo mailer, which was a fixture bootstrap issue.
- Existing real-WordPress `ConversationConcurrencyTest`: 3 tests / 42 assertions PASS after the cookie-only reader seam.
- Focused tools unit bootstrap/conversation tests: 14 tests / 52 assertions PASS.
- Anonymizer suite: 19 passed; new snapshot/override fields are emptied and operational enable/heartbeat options omitted.
- Service native-channel contract/deadline tests are part of the full Genie suite. The real name-field-only synthetic scam call returned suspected_spam/fraud_or_phishing in 3.509695s using `typesafe/jev-1.13-20260917`; see `name-field-live-jev.json`. It uses a non-resolving `.invalid` URL, never the actual incident link or a customer's identity. One case is not a production accuracy measurement.

## Computer Use

A guest actually submitted the English contact form and saw its existing success message; CUA click-to-return was 0.858s (not server-only timing), see `customer-submit-timing.json`. The PHP integration fixture separately proves zero Jev HTTP calls in the customer submission. Email recipients were asserted in Outbox data; local TestMode rewrites outbound delivery to one synthetic tester and the local isolation plugin writes mail to disk.

`mail-{en,de}-{normal,suspected_spam,uncertain}-{390,1440}.jpg` are actual Woo email renderings, captured via Computer Use. They are fixtures of the real template, not inbox delivery claims. The staff screen was used to save a genuine correction in both languages; the raw spam result and inquiry-received status remain, and the correction/note controls retain their saved values. Original JSON uses native WordPress readonly textarea styling to remain readable on phones. `staff-correction-*` contains the screenshots.

Customer composition/styles have no source changes. `contact-*.png` are lossless captures of the same local snapshot with the feature off/on, at exact 390/1440 widths, after scrolling to reveal the footer. `customer-parity.json` records every pixel difference without masks. This is a feature-regression comparison, not a new claim that all live/local site page types passed the absolute reproduction gate. Any nonzero capture must remain reported, not rounded away.

## Review repairs

The independent full-diff Standards review found a database namespace missing from the server-wide advisory lock and duplicated conflict logic. Both were repaired by following the existing Genie lock naming pattern and extracting one conflict predicate.

The independent Spec review found a partial Outbox storage failure could suppress a notice, unrelated account history could enter an ordinary inquiry, and queue delay was not recorded. The final implementation reads back the message and inquiry ledger before commit, rolls back a failed write while retaining PENDING, uses only an explicitly linked or signed browser-selected owned thread, and records worker started_at/queue_seconds separately from service seconds. The real fixture injects the failed message-meta write and proves subsequent recovery creates exactly one logical team notice. Follow-up review results are in `review.md`.

## Deployment boundary

The feature defaults off. The deployment owner must deploy both service and plugins, install/verify independent once-per-minute CLI recovery and normal due-cron, and only then enable it. A missing/stale recovery heartbeat or service configuration takes the normal immediate notification path with unable-to-assess. Ten seconds is the classification window, not a promise of inbox arrival within ten seconds; scheduler, mail quota and SMTP travel remain independent. See the spec's activation/rollback instructions. This branch has not merged or deployed.
