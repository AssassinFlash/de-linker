# Native CSV workflow increment

2026-10-23. Implemented against
[`548-profile-intake-workflow.md`](../../../specs/548-profile-intake-workflow.md).
Final fixed-source Spec/Standards review and the native browser matrix pass for
this increment; the rejection/fix history below is preserved.
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

## Fixed-source rejection at d04c327f

Standards found an executable render/layout/passive-effect interleaving: native admission could be withdrawn after render-time admitted=true, yet an old cached owned preview still received focus/scroll and was marked revealed. No RPC/ACL disclosure was established. Spec independently found completion feedback stranded across same-scope verification; it then replayed on Undo and moved focus to the import trigger. Both are P2 and that fixed snapshot remains rejected.

The correction supplies stable live admission callbacks to the shared reveal operation, rechecks at the actual focus/scroll boundary, and records an asset revealed only after success. Intake also tracks render-time admission as a dependency so same-scope verification resumes and consumes its pending feedback. Interactive errors use the same live guard. Real React regressions cover native withdrawal between render and effects for both cached result and error, plus delayed same-identity verification consuming completion before Undo. Native full fresh-file mapping→source interpretation→Use→Save already reached server revision7; final corrected runtime readback and new fixed-source reviews remain separate gates.

## Final scoped acceptance at 432d8629

Both independent axes pass fixed `432d86294da8200bea20cc35c0f7b550cbf9bec5`.
Standards replayed the original layout-withdrawal probe unchanged: current
admission false, no focus events. It also challenged disconnected targets and
synchronous withdrawal during focus. Its isolated archive passed 25 Node,
32 existing React cases plus the original probe, an additional reveal-boundary
probe and the build manifest check. Spec replayed its original outside-act
React 19/StrictMode/SessionBoundary/ProjectEditor/PlannerClient interleaving:
completion waits during verification, resumes once the same scope is verified,
and Undo preserves user focus. Its independent 25 Node/32 React suite and live
guard/disconnected/retry probes passed. Neither axis treats DOM tests as layout
evidence or repeats unchanged backend tests.

The native WP runtime was refreshed at this fixed source. All four EN/DE ×
1440×1000/390×844 interpretation views show saved project revision 7; the
original source hash, mapping, captured TZif and quality facts survive refresh
and language switching. A full fresh DE390 file chooser→column preview→explicit
mapping→interpretation→Use→Save path produced that revision. The successful
interpretation heading began at y209.99 below bar194; the selected-draft notice
at y219.89 below the wrapped unsaved bar204.39. Final-code cancellation returns
focus to Import at y209.82 below bar194. The prior 36bea12c EN/DE error matrix
proves unchanged visual error margins; it is identified separately from the
final-code lifecycle checks rather than relabelled as a fresh final-code run.

The synthetic two-row Oslo fall-back fixture interprets explicit offsets as two
different UTC intervals: signed net energy1kWh, covered0.5h, gap0.75h, one gap,
interval means−4/8kW, native15min. It is never labelled actual meter data, gross
load, a peak guarantee, annual consumption or engineering suitability. No gap
was filled. The transient local filename is absent from saved metadata.

Curated native screenshots, visible readback, fixture and source/build hashes
are preserved in [profile-native/acceptance.json](profile-native/acceptance.json).
The runtime script SHA-256 was compared with the built file, not inferred from
an app version. Strict TS/Vite, all three source manifests and gettext coverage
pass (236 source messages, zero catalog gaps/JSON problems). The backend remains
the independently accepted 323 planning tests and real ASGI/concurrent CSV
probes at 0446; PHP gateway evidence remains289/2357, unchanged thereafter.
No production write, live tool cutover or real mail occurred. This closes the
intake increment only. Native login/cross-identity unknown intents and the
remaining A–D work remain inside the active whole-delivery goal.
