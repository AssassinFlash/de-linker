# Review of persistent manual roof drawing

Full increment base: `43297ecf5673fa5f29c82f90fbe583666a5e3e15`. Final source/style pin: `716ae5f456377339f5b41b85430fbb3e92e0ea67`; unchanged application/build pin: `726e326b5c3ce322a2e1471008483a10e9e3c3b1`. The Spec and Standards axes were independent reviewers. One free execution slot required sequential reviews; they were not simultaneous.

## Standards

[Full implementation review](review-standards-02c87049/REVIEW.md), [validation/result-placement addendum](review-standards-786d0db9/REVIEW.md), [repeated-success addendum](review-standards-726e326b/REVIEW.md), and [final phone-style addendum](review-standards-716ae5f4/REVIEW.md): **0 documented-standard findings; 0 Fowler heuristic findings**. Each retained report identifies its actual pin and limits.

The independent reviewers checked the installed library API boundary, one project geometry writer/history, native identity grants, exact journal CAS and retirement, explicit source/plane inputs, locale records, token/WindPress isolation and source/build identities. Focused tests were executed by the reviewers and remain in their checks files. The full base-to-final `git diff --check` still identifies trailing whitespace in bundled MapLibre shader text at `MapViewport-DEU-DlpF.js:62`; this generated-vendor diagnostic is recorded, not described as a clean full-diff check.

## Spec

The [first pinned review](review-spec-9efd14fc/REPORT.md) found a P2 uncertain-write sequence: A committed with unknown acknowledgement, newer B lost A's exact retry intent, and public Retry remained conflicted. The [independent repair probe](review-spec-b48ffda6/final-recovery.json) proves repeated unknown A acknowledgements are settled exactly before B. It separately proves a genuinely competing tab is neither overwritten nor deleted and an explicit fork retains both versions. **Closed** by the pending-intent repair.

The [later pinned review](review-spec-786d0db9/REPORT.md) found a P2 repeat-success boundary: Undo → Resume → unchanged resubmit committed a roof but the boolean reveal trigger did not fire a second time. The [independent final probe](review-spec-726e326b/repeat-submit.json) proves both successes focus the result and common geometry changes retain truthful status without stealing unrelated focus. **Closed** by the successful-application counter.

[Final JavaScript review](review-spec-726e326b/REPORT.md) and [final phone-style addendum](review-spec-716ae5f4/REPORT.md): **0 new or unresolved source-contract findings** in this increment. Earlier failed pins and unique probes are retained, not overwritten by passing evidence.

## Verification and boundary

The final JavaScript run in `tests-output.txt` passes **214 tests: 88 domain/data and 126 DOM/controller tests**, with no `act` warnings. TypeScript/Vite build, emitted-module identity, formatting and i18n coverage pass. Source/build digests are retained in the independent snapshots. No dependency, global React, model route, service architecture, production or mail change occurred.

[Native evidence](NATIVE.md) separately records one-point reload/cross-language recovery, actual map vertex/midpoint editing, field-error placement, real geometry-service application, shared plan/3D/history, pre-confirmation recovery, saved revisions 4 and 5, phone repeated application, native WindPress generation, and cached map/3D reentry. Fake IndexedDB and fake Map/engine fixture claims remain distinct from native execution.

The entire four-combination state matrix and native geometry-refusal/provider/touch paths are **not passed** by this report. The active full goal still includes existing-ring/hole/obstacle/keep-out UI, provider/imagery coverage, calculation/equipment/BOM/report/PDF consumers, site integration/migration, review and production readback. This source increment and its positive native paths do not close those obligations.

Standards findings: **0**, no worst finding. Spec findings: **2 P2 found and closed; 0 unresolved source findings**, with native/full-goal acceptance still open.
