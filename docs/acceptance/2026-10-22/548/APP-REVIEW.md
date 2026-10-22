# Project workspace implementation review

2026-10-23. This increment is project/brief/edit/save/recovery, not a completed
vertical path A or the completed engineering tool. CSV intake UI, map/2D/3D,
linked calculations, qualification, reports and the full site/release paths
remain required inside the active delivery goal.

## Standards at ee161e5b

Not accepted. The independent reviewer reproduced two P2 findings: focus or
visibility rechecking unmounted the editor, losing delayed writes and invalid
raw numeric text; and existing PO translations were absent from this app's
native script JSON. It independently ran all 24 Node fixtures and a real
strict-TypeScript/Vite build, reproducing the committed bundle byte-for-byte.
React isolation, scoped WindPress styles, native PHP presentation boundaries,
build order and absence of new legacy identifiers passed. No further blocking
smell was identified.

## Spec at ee161e5b

Not accepted. The independent reviewer reproduced four findings with actual
React 19/StrictMode/JSDOM/Client fixtures: P1 unsaved edits disappearing when
IndexedDB was unavailable and the same identity was rechecked; P2 creation
stuck in local authentication failure with no re-bootstrap; P2 seven messages
missing from the native module JSON; P2 the 72px project bar appearing after
its one-time observer setup, leaving the anchor-height variable at zero.
No scope creep was found. Independent copy comments are incorporated in
APP-COPY-REVIEW.md, including the annual-total/bill wording correction.

## Corrections under re-review

Identity verification now immediately hides and makes the existing workspace
inert while retaining its editor state. A successful same-scope bootstrap
restores that instance; an explicitly different confirmed identity clears
the old private cache and mounts a new editor. Failure keeps the old content
hidden for retry. No identity is inferred from the cached document.

NewProject explicitly rechecks native identity after 401/403/session change.
It retains the frozen creation intent and waits for the customer's explicit
retry; it does not automatically replay a mutation. The project bar uses a
React 19 ref lifecycle and ResizeObserver on the actual mounted bar, including
font/responsive/visibility changes and cleanup.

All seven missing messages now have an additional native planner-script
reference while retaining existing German translations. Coverage checks every
app source message against that actual generated script catalogue. A real
WP-CLI fixture reproduces a reused message bound only to the old script, then
verifies the corrected binding. Native JSON generation is not replaced.

The implementer's checks now include 24 domain/protocol tests plus five real
React/DOM lifecycle tests, strict types, formatting, production build, 14
native gettext-gate fixtures and three extractor fixtures. The lifecycle
fixtures inject storage/network failure and measured DOM heights explicitly;
they do not stand in for real responsive-browser acceptance. The owned p548
native integration was rerun: 12 passed in 55.92 seconds. No production write
or real mail was used. Both independent axes must confirm the new fixed
source before recording this component as accepted.

## Independent findings at ef4ddc74 and 9db9d479

At ef4ddc74 Standards passed the original corrections. Spec independently
closed all four original findings, including all 98 source messages being
bound to the actual module catalogue, but reproduced a new P2: an old
creation acknowledgement waiting on local cleanup could refill the former
scope's cleared cache and change the current URL after identity B mounted.
The B interface did not display A's project content.

At 9db9d479 the unmounted-instance completion was fenced and Standards
passed. Spec reproduced a narrower window with a native focus event:
identity B confirmed and the cache cleared, then the old cleanup completed
before React committed B and ran A's cleanup. The lifetime check alone still
allowed the old cache/navigation callback. This fixed source was not accepted.

The next correction pins every query/mutation to its opening confirmed
scope in PlannerClient. A synchronous current-confirmation check also guards
cache writes, revision acknowledgements and navigation. The old component's
props or cleanup timing cannot grant admission. Both delayed creation stages,
a delayed revision write and an awaited close run through the pre-commit
window in actual React/Client fixtures, with event ordering asserted before
an act flush. Query notification timers in the fixture now belong to its
JSDOM page, matching native page disposal instead of calling a subscriber
after its global window has been removed. These checks pass: 25 Node tests,
13 DOM lifecycle tests, strict types, formatting and production build.
Independent re-review remains required for this correction.

## Browser evidence for the project/brief surface

The owned snapshot instance at port 9347 was exercised with native
WordPress/WooCommerce sessions in EN/DE at 1440 and 390 pixels. This is
project/brief acceptance evidence, not completion of path A or the whole tool.
The synthetic Norway commercial project was created, saved to revision 3,
refreshed, locally edited, closed/reopened with recovery, and undone back to
its confirmed document. EN mobile then saved revision 4 and refreshed to the
same exact note. German displays 150000,5 while English displays 150000.5;
switching languages retains the same project ID, country and time zone.
German input 1.000 shows an error and disables save; Escape restores the last
valid value. The mobile new-project form and project index were checked too.

Two browser-only defects were found and fixed in 9db9d479: the section ID
was on h2 while margin belonged to its section, and native unlayered chrome
CSS overrode the layered margin. Targets are now focusable sections and the
strictly app-scoped margin includes both measured bars. At 1440 the header
is 89px, project bar 73px, target margin 178px and heading top 206px; at 390
they are 81px, 113px, 210px and 242px respectively. German nav min-content
also widened a mobile grid to 424px; minmax(0, 1fr) plus min-width: 0 now
keeps document, aside and main exactly 390px, with only the nav itself
scrolling. WindPress was natively recompiled and the browser reloaded.

Screenshots are in artifacts/548/workbench: en/de-desktop-1440.png,
en/de-mobile-390.png, de-mobile-load-390.png, de-mobile-invalid-390.png,
en-mobile-saved-390.png, en/de-desktop-projects-1440.png,
de-mobile-projects-390.png and de-mobile-new-project-390.png. The existing
Genie launcher opened and closed alongside the isolated runtime; no prompt
or mail was sent. Its coexistence screenshot is en-desktop-genie-1440.png.
The inspected browser error log was empty. Viewport override was reset.
Real guest/account UI claim, creation recovery across tabs, source intake
and the remaining engineering/site paths are still inside the active goal.

## c165f6dc review and the next recovery increment

Spec independently passed c165f6dc, including its own actual-Client native
focus probe and a direct old-scope request that performed no fetch. Standards
confirmed that scope issue was closed but found another P2: a deferred close
refused while the same native identity was being verified left ProjectEditor's
closing flag true. The original data stayed intact, but Projects remained
disabled. The current close callback returns whether navigation occurred;
the editor resets closing after a refusal. An actual-Client/React fixture
holds both local flush and native bootstrap, verifies recovery with the
original note and URL, and then actually retries the close successfully.

The current local creation store also uses an immutable per-scope/UUID queue.
The former one-row-per-scope record could lose one unknown creation when two
tabs submitted concurrently. Schema 4 adds the indexed queue and atomically
migrates valid schema-3 creation bytes while preserving existing project
drafts and invalid legacy records. Reads stay inside the confirmed scope;
there is no enumeration of another identity's unknown creation. A UUID with
different bytes conflicts locally. Acknowledgement deletes only its exact
body, and a full queue is reported rather than evicted. The initial browser
resource policy is 128 intents and 8 MiB total creation bodies per scope;
these are recovery storage policies, not account or engineering capacities.
Several unknown creations are selectable and require explicit replay.

Implementer checks now pass 25 Node tests and 15 real React/DOM tests, strict
types, formatting, build and native gettext coverage/validity/copy gates.
Seven native IndexedDB fixtures ran through CUA on the isolated Vite test
origin at port 9345: blocked-upgrade retry, v3 draft/creation migration, two
connections/concurrent creations, byte conflicts/late deletion, scope
isolation/legacy acknowledgement, bounded queue and preserved invalid legacy
bytes. The fixture page has no planner API calls or production entry.
The final status and seven PASS rows were observed in the browser and saved
to artifacts/548/workbench/native-storage.png; its synthetic database was
removed by the fixture and the temporary tab closed.

Real p548 pages were also used in two tabs. A short-lived MU transport fixture
refused only loopback p548 project-creation calls, under local PHP-server,
host, port and expiry guards. Both pages preserved different unknown intents.
After refresh both appeared in the real DE selector, then in EN. The fixture
was removed before retries and its absence verified. B was explicitly retried
first, yielding project 9dd8cfe9fed1452ebc9a20fa40d1a9b3 revision 1; A still
remained and yielded 2db4d16f1e06407aa79e7daf3464d74a revision 1. A still-open
old page retried B's frozen request and received the identical B project ID
and revision 1, without another project. The index showed exactly A, B and
the earlier Oslo fixture. Queue confirmation restored the New project button.
No account or mail was created. The native WindPress cache was compiled at
1792708364; the new form spacing and selector were checked in EN/DE at 390px,
document width exactly 390. Browser screenshots are
de-mobile-creation-recovery-390.png, en-mobile-creation-recovery-390.png,
en-mobile-recovered-projects-390.png and stale-creation-same-project.png.
Temporary viewport overrides and auxiliary tabs were cleared afterward.

This correction and queue increment still require both independent axes at
the new fixed source. Guest/account browser claim, cross-identity unknown
creation reconciliation, CSV intake, maps/2D/3D, calculations, equipment and
all site/release consumers remain required within the active overall goal.

## Independent acceptance at aefd6f26

Both axes passed fixed aefd6f260bdaaefce50d8fa85e72f01f3fc25714.
Standards independently closed the original same-scope close probe and found
no remaining hard-standard issue or separate smell. Spec independently
confirmed the same close, retained note/URL, successful retry, all four
native-focus scope-window paths and explicit exact-wire creation recovery.
Each ran 25 Node and 15 DOM tests plus strict types and source/build checks;
the fixed bundle was independently reproduced. Spec checked all 99 actual
module messages and passed the new EN/DE copy. Native IndexedDB and the
real p548 multi-tab execution evidence above remains the implementer's CUA
record; component acceptance does not claim complete A or production release.
