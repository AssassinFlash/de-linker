# Spec addendum: b57d7dbf

Reviewed `git diff 55104bbdbbf9e694eba4785787daaaf109b99ed8...b57d7dbfe20559ff513b2122500c57fd708996c7`, comprising `2b08e309` and `b57d7dbf`, against the complete updated specification and current main AGENTS. This supplements the independent base-81524ca9 review; its report, 17 real-engine scenarios and initial harness failure remain preserved.

**Confirmed findings: 0.**

(a) **Missing or partial requirements:** No new missing implementation requirement was demonstrated. Spec lines 11–12 require: “The selected roof and feature type remain visible while collecting corners and after restoring an unfinished drawing, before the properties form opens.” The shared `mapFeatureContext` renders that context in the drawing controls for every v3 phase and reuses it in properties. Three focused actual React/journal/controller tests independently pass for new and restored openings, obstacles and keep-outs.

(b) **Unrequested behavior:** None found. The shared `mapDrawingTextLimit` retains the pre-existing 4096-character raw cap in roof/feature readers and their forms; the documented server transport source uses that same cap. `canStartDrawing` preserves the identical disabled/checking/storage-failure/geographic-readiness conditions for all three drawing entries.

(c) **Implemented-looking but incorrect requirements:** None confirmed. Eleven roof/feature domain tests pass, including strict recovery, original locale, unchanged source/plane, stable identity, invalid raw text and prepared-result rejection. Build/source-manifest verification and the built-module test pass. No projection, command, review-service, journal or engine implementation changed; unchanged true-engine scenarios were not rerun.

These tests use JSDOM and the labelled MapLibre port. Native EN/DE desktop/phone appearance, HTTP/server consumers and full-goal acceptance remain separate evidence gates. Spec lines 37–39 explicitly retain the remaining engineering, country, report, site-consumer and production obligations. Root's native observation and screenshot are not claimed as this reviewer's independent proof.

Only this addendum directory was written. No source/build/browser/runtime/dependency/settings changes or additional instance/copy were created. Source/build identity is recorded in `identity.json`; review ownership is released.
