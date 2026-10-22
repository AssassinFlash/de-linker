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
