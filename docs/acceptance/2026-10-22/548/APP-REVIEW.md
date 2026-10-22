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
