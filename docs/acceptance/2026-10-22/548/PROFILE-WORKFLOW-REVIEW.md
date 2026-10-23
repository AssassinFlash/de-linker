# Native CSV workflow increment

2026-10-23. Implemented against
[`548-profile-intake-workflow.md`](../../../specs/548-profile-intake-workflow.md).
Fixed-source Spec/Standards review and the final browser matrix are pending.
This record does not close path A or the whole unified-workbench goal.

Mature intake research used Apify for all search/retrieval: eight official
PV*SOL, OpenSolar and SAM pages, exact source/index hashes and documented limits.
None was represented as a competitor CSV session performed by us. The adopted
pattern separates file/structure, explicit meaning, interpretation and project
adoption; the source timezone, signed boundary, permanent receipts and gaps
follow this site's already verified service contracts.

Implementer evidence so far:

- 321 real planning tests passed in 15.48s, including whole-file structure
  validation beyond the displayed sample, owned read before base64 decode,
  no preview writes, cross-project source refusal and signed-source role refusal.
  Published import/selection JSON schemas are compared with actual service models.
- Strict mypy passed over 66 planning modules; ruff passed.
- 25 Node domain/client tests and 22 real React DOM tests are the current
  suite composition. The seven new intake cases cover explicit mapping, exact
  lost-ack retries, selection before recovery cleanup, native identity fencing,
  delayed same-scope hydration, failed replacement clearing the prior file and
  persistent authentication failure avoiding an automatic recheck loop.
- Nine native IndexedDB fixtures passed through Computer Use at the isolated
  development origin: version 3→5 upgrade, creation continuity, blocked upgrade,
  parallel connections, exact-body acknowledgements and conflicts, scope/project
  isolation and capacity refusal without eviction. Fixture cleanup removed only
  its synthetic development-origin database, not the WP-origin project store.
  Screenshot: `artifacts/548/workbench/native-storage-v5.png`.
- Native PHP suite: 289 tests / 2357 assertions. Gateway WPCS passed.
  PHPStan's first invocation hit its default 128 MiB process limit; rerun with
  the command-local 512 MiB option passed, without changing php.ini or analysis
  level. German-copy and catalog validity passed; runtime coverage is rechecked
  after the final build.

Actual CUA exposed two defects before acceptance: the native file-button text
followed the browser's Chinese locale on the German page, and the desktop
project rail scrolled out of view at the long-form intake section. The native
input now retains keyboard/file-chooser semantics beneath a localised site
control; its filename is temporary page state only. Field labels are separately
bound from option/helper text. Desktop project navigation is sticky beneath
the measured site/project bars; mobile remains a normal-flow layout. These
changes require fresh CUA proof, not an inferred pass from CSS or a build.

All customer copy passed an independent adversarial draft review and parent
selection in `PROFILE-COPY-DRAFT.json` / `PROFILE-COPY-REVIEW.md`: 235 current
source messages, with the original 99 unchanged. Actual per-script gettext,
source/save semantics and EN/DE visual execution remain separate gates.

Owned p548 was restarted and its WindPress volume recompiled through the native
admin pipeline. No production write or real mail was performed in this increment.

## Fixed-source rejection at a3602a4d

Both independent axes rejected that snapshot. Standards reproduced the
unprotected asynchronous file-read stage and a rejected request remaining in
the selector after its recovery record was removed. Spec also reproduced typed
input refusal being held hostage by unavailable browser cleanup, a completed
server save still blocked by the import close guard, and Python csv's implicit
131072-character cell ceiling rejecting a legal source below the declared limits.

The correction adds byte-read protection, revokes rejected durable state before
best-effort cleanup, removes stale selector entries, and passes only baseline
server selections into intake. An owned receipt plus that confirmed baseline
allows completion independently of IndexedDB. Merely editing the selection
does not. A shared stdlib-reader factory monotonically raises csv's process-wide
field ceiling under a lock to the bounded source length; smaller concurrent
sources cannot lower an active reader's limit. These changes require a new
fixed-source review; this history does not retroactively pass a3602a4d.

Correction checks: 323 planning fixtures passed in 14.48s; strict mypy passed over 67 planning modules. The full app suite passed 25 domain/client and 26 React DOM cases. Four added rendered regressions exercise pending file bytes and reload, typed refusal with failed storage, stale selection during delayed cleanup, and a full ProjectEditor import→selection→server Save→close with every local write/cleanup unavailable. An actual private ASGI fixture previews an unchanged 140000-character cell, imports the same source hash and returns 1 kWh without a project revision; concurrent readers preserve their large/small cells. All three build-manifest checks, German-copy and eight gettext catalogs passed. New fixed-source reviews and the final native matrix are still pending.

## Fixed-source review at 0446aac8

Standards passed: independent 323 planning (14.73s), 25 Node and 26 React cases, original file-read probe and independent slow-cleanup/stale-selector probe. Spec independently closed all prior failures, including unchanged 140k source bytes and 1 kWh, plus four concurrent readers to 500k characters, but rejected one newly reproduced state error: after Undo removed a selection, the intake component still announced it was selected in the open draft. That snapshot remains Spec FAIL. The correction now also receives current draft selected IDs; a historical component selection cannot display either selection notice when absent from the current draft. Server baseline IDs retain their separate saved-proof role. A real ProjectEditor regression covers Use→Undo→Redo→Save→Undo→Redo and verifies actual selection controls and both notices at each state.

## Fixed-source review at 4960a589

Both axes independently passed. Each ran 25 Node and 27 real React cases. Spec additionally replayed its original Undo probe unchanged (actual selection false, selected notice false) and an extended Use→Undo→Redo→Save→Undo→Redo→Remove→Save probe, ending at server revision 3 with no selection/notices. Unchanged backend evidence remains the independent 323 planning suite and real ASGI/concurrent-reader probes at 0446.

Native 390px testing then exposed a further usability defect: after a user submitted at the bottom of the mapping form, the 422 error was rendered about 1470px above the viewport and received no focus. The user could not see why import failed. The correction gives only user-triggered intake errors programmatic focus; background owned-profile query errors do not steal focus. The actual React test now asserts focus reaches the safe error text while correction fields remain. Fresh native error visibility proof and fixed-source review are required before acceptance.

Plain focus alone was also rejected by native evidence: the 390px error occupied y=-89…162 behind a project bar ending at y=194. The final correction focuses without implicit scrolling and explicitly scrolls the error to the start, sharing the measured site/project scroll margin. Native WindPress compilation 1792715470 produced 730361 bytes (31143ms); no shared Redis resets/config changes were used. Actual EN390 error bounds are y=210.16…461.73 with bar end194; EN1440 y=178.16…343.95 with bar end162. Both full errors are visible and the original correction fields remain. Twenty-five Node and27 real React cases pass; JSDOM explicitly has no scroll/layout implementation and does not substitute for this native proof.

## Fixed-source review at 36bea12c and action-result continuation

Both axes passed 36bea12c with independent 25 Node/27 React suites and extra default/opt-in/error-rerender/private-text focus probes. DE1440 error y178.16…365.39/bar162 and DE390 y210…504.45/bar194 were then verified in native CUA; document width matched each viewport.

Native success testing exposed the same structural scroll-loss after long-form collapse: import success, then Use, could leave the user in the site footer. Completion now reveals the first interactive interpretation heading once per owned asset, then the selection notice (or import trigger after explicit cancellation). These action targets share one measured scroll margin and a small common native reveal operation. Background owned previews and interval pagination retain user focus; Undo/Redo does not replay completion focus. Other pending imports remain durable and require explicit selection/retry rather than automatically opening the next one after completion. Full app checks pass25 Node/28 React, including first interactive result, background loading, repeated render, next/first page, cancellation and history focus. The first recovered DE390 interpretation heading was measured at y210.19/bar194 with original1kWh result; final full fresh-file→Use→Save native proof remains required. No production changes or real mail.
