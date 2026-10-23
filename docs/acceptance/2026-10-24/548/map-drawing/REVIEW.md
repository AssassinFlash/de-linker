# Map drawing source increment: final review and readback

Source pin: `71cd719aa67021aee6398ae58f359738005d1f57`.
Fixed base: `66324a39fb449425dd1144b46b4d3abc21dc52d0`.
Complete diff: `git diff 66324a39...71cd719a` (11 files, three commits).

This accepts the deliberately unmounted metric-command/controller increment
under the active unified-workspace and whole-site map. It does not accept a
complete customer drawing flow or close the full goal. The prior Spec P2 and
Standards P3 were fixed and independently rechecked; their failing evidence is
retained beside the final reviews.

The reviews were independent and sequential: the platform rejected the parallel
Standards dispatch because two unrelated pending-init agents occupied slots.
No replacement checkout, dependency copy or local instance was created.

## Standards

Canonical report: [review-standards-71cd719a/REVIEW.md](review-standards-71cd719a/REVIEW.md).

# Standards: PASS — no open findings

Reviewed the full eleven-file `git diff 66324a39fb449425dd1144b46b4d3abc21dc52d0...71cd719aa67021aee6398ae58f359738005d1f57`, covering `c562676a`, `2464009a` and `71cd719a`. This reuses the exhaustive prior nine-file review and independently verifies every corrective hunk. Current root AGENTS, CONTEXT, the isolated-runtime ADR and existing domain/data conventions apply; no CONTRIBUTING/CODING_STANDARDS file exists.

**Hard documented breaches: none open. Previous P3 closed.** `apps/planner/src/data/MapPickGate.ts:3` now owns the independent gate class; `MapDrawingController.ts:75` is its file's sole class, and the test imports the gate directly. This satisfies root `/Users/chesterjohn/Documents/de-linker/AGENTS.md:78`. The probe verifies the gate body moved byte-identically, the controller differs only by its removal and the test differs only in imports. Previous failure evidence remains intact.

**Fowler baseline judgment calls: none justified.** All twelve supplied smells were considered. The new file reflects the existing viewport/controller lifetime boundary without adding indirection or changing behavior. The domain reconciliation, command conversion and SDK lifecycle responsibilities remain separated. No additional extraction, domain wrapper or dispatch abstraction is warranted by this diff.

The unchanged implementation preserves original metric points, whole-frame command refusal and the existing project writer/history. Real installed-library callbacks, display precision, final-endpoint reconciliation and cleanup error boundaries retain the prior independent audit. The research update explicitly distinguishes its historical snapshot from current installed/import/map/controller state, and keeps future design and acceptance claims bounded.

Independent probes checked all 107 source hashes and seven build hashes; all seven emitted artifacts are byte-identical to base. All 22 real-Terra/JSDOM controller tests were reexecuted successfully through the new imports. The previous twelve domain tests remain bound to identical source; the owner's current 195-test/build/build-check/format receipt was inspected without repeating the unchanged full suite. No legacy identifiers or high-confidence secret patterns were found in the full changed hunks.

No source copy, install, worktree, stack, network or application change was made. The controller remains unmounted. This is Standards source/library acceptance only; customer UI/recovery, native/GPU/physical touch, engineering/country/provider permissions, production and whole-goal acceptance remain outside this verdict.

## Spec

Canonical report: [review-spec-71cd719a/REVIEW.md](review-spec-71cd719a/REVIEW.md).

# Final Spec review — 71cd719a

**PASS for this internal source increment; zero actionable findings.** Reviewed the complete `git diff 66324a39fb449425dd1144b46b4d3abc21dc52d0...71cd719aa67021aee6398ae58f359738005d1f57`: three commits, eleven files, against the source SPEC and the implementation/controller dossiers. All 107 source hashes match current pinned Git bytes; seven emitted artifacts remain byte-identical to the base. The controller remains unmounted.

The prior P2 is closed. Re-ran the same independent DOM/Map-port fixture with **real installed Terra Draw 1.35.0 and MapLibre adapter 1.4.1**, retaining the old failing evidence unchanged. Adapter `removeLayer()` refusal during interruption, endpoint failure and public disposal now yields exactly one terminal failure, zero uncaught DOM errors, no late transaction or duplicate notification, unchanged prior raw input, restored handler/cursor states and a reachable owner `remove()`. Ordinary cancellation yields one interruption without failure. A refused pan restoration no longer skips the other handlers or cursor. Construction failure retains both the original invalid-ring cause and cleanup refusal. This satisfies SPEC §10: “report cleanup/restoration failures through one terminal failure notification” and “allow the owner to finish removing that map”.

The actual-adapter positive control also preserves the precise release endpoint, ring closure and untouched vertices, then removes all three sources/five layers normally. Independently executed **34 focused tests, all passing**: cyclic/reversed rings and every insertion/deletion edge, exact untouched UV values, 20,000-vertex budget, source/plane/extrusion preservation, stale whole-frame refusal, grouped undo/redo, provisional-vs-completed events, midpoint coalescing/target refusal, endpoint correction, cancellation and disposal. `MapPickGate` separation preserves its later-physical-pointer reset contract. The historical-status clarification avoids treating old dossier gaps as current capabilities.

Commands: `node docs/acceptance/2026-10-24/548/map-drawing/review-spec-71cd719a/probe.mjs`; from `apps/planner`, `node --test src/domain/mapDrawingGeometry.test.ts src/domain/mapRingEdit.test.ts tests/map-drawing-controller.test.mjs`. Exact results/hashes are in adjacent JSON/logs.

Acceptance remains **source/library/domain only**, as SPEC lines 12–14 require. No new runtime mount, customer drawing/recovery flow, native/physical-touch or topology/engineering acceptance follows. Complete same-project drawing/save/reopen, providers, full #548/site consumers and production gates remain open under SPEC’s acceptance boundary.

## Validation and runtime boundary

- Full application tests: **195 PASS** (83 domain/data + 112 DOM/controller).
  New focused cases: **34 PASS** (12 domain + 22 real Terra Draw controller).
  [Exact test output](tests-output.txt).
- Strict TypeScript/Vite build, source/build manifest check, one real emitted
  lazy-module identity test and formatting passed. Vite's existing large-chunk
  warning and Node's fixture-only module-type warning remain explicitly recorded
  in [validation.json](validation.json); they were not suppressed.
- All **107** source manifest entries and **seven** emitted artifact hashes were
  read back. All prior source hashes and all seven emitted bytes are unchanged
  from the base; only the four new internal runtime modules were added to the
  source receipt. The controller is not imported by the customer application.
- The existing local identity/map/native evidence remains a distinct earlier
  acceptance. No fresh screenshot, live drawing, physical-touch, durable raw
  recovery, topology/engineering release or production acceptance is claimed.
- [Source audit](source-audit.json): zero introduced legacy markers or
  high-confidence credential patterns in the complete source increment.

## Retention and continuation

No new instance, worktree, snapshot or dependency installation. Keep the existing
owned p548 instance for this active map and the approved Journal prototype for
comparison; release them when that use ends. Two superseded development/temp
test logs were removed after the final output was retained. Available disk
space read 825 GiB then 830 GiB; that observed increase includes concurrent work
and is not claimed as this cleanup's saving. The retained review evidence is
small, with separate old-failure and final-success probes serving distinct
purposes.

Next required work on the same map is the mounted customer drawing/review flow,
scoped raw draft persistence and recovery, source/plane confirmation, same-project
2D/3D/history/save/reopen, native EN/DE desktop/phone/touch and provider/style
failure/withdrawal checks. Energy/country/equipment/BOM/report/PDF, affected
site/Genie/Woo/draft/inquiry consumers, migration, review site and production
backup/deploy/readback remain part of the original full goal.

**Final review totals:** Standards hard violations 0 and supported smells 0;
Spec actionable findings 0. Full-goal state remains active.
