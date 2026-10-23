## Spec addendum

Pin: `716ae5f456377339f5b41b85430fbb3e92e0ea67`; previous source review: `726e326b5c3ce322a2e1471008483a10e9e3c3b1`. Reviewed `git diff 726e326b...716ae5f4`: only the planner CSS and incremental SPEC changed.

**Findings: 0.** [SPEC:13](../SPEC.md) requires “At the 390-pixel phone viewport, roof properties use one column” while retaining desktop and site styling. `plugins/linker-commerce/content/windpress/planner.css:405–408` adds one rule inside the existing `components` layer and `max-width: 640px` media query. Its `[data-linker-planner] .lp-drawing-properties .lp-geometry-fields` selector matches both field groups in `MapRoofProperties.tsx:98,156`, overrides the earlier two-column mobile rule, and applies one `minmax(0, 1fr)` track. The drawing-form scope leaves other geometry forms and site surfaces unaffected; widths above 640 retain their existing grid.

Verification was read-only diff/cascade inspection. Source CSS SHA256: `6dadc4a210a067a8a831ef3834f3c28912f6d096ac1cb188145df99b998e2bb2`. Application JS, tests, emitted build and locale files are byte-identical to the preceding reviewed pin. Both earlier source P2 closures therefore remain unchanged. Earlier reports and probes were preserved; no tests or probes were added for this CSS declaration.

The owner's native WindPress generation and 390-pixel readback remain separate evidence. This source addendum does not establish compiled-browser readability or pass the entire native matrix. Native geometry refusal is still unproven under [SPEC:25](../SPEC.md); no engineering, production or whole-goal completion is claimed. The full goal remains active.
