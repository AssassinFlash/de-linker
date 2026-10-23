# Native drawing readback

Local p548, WordPress 9347 / engine 9348, owned synthetic project `82a84c56e50c4efb8497d1bfbe106bd1`. The test coordinates, roof properties and source declarations are synthetic; they are not a surveyed building. No production, inquiry, email or external imagery action was performed. This is evidence for an increment within the active [full workbench goal](https://github.com/AssassinFlash/de-linker/issues/548), not whole-goal acceptance.

All UI actions used the existing CUA in-app-browser tab 2. Screenshots came from that tab's native Page capture at the observed viewport and scroll position. The 390 × 844 checks use browser device-metric emulation and mouse/native accessibility actions, not a physical touch-device claim. The desktop viewport is 1440 × 1000.

## Observed paths

| Path | Actual observation | Evidence |
| --- | --- | --- |
| DE desktop partial recovery | Started empty; recorded one real map-centre point; paused, really reloaded, reopened the saved one-point drawing, and appended two physical map clicks. The saved project remained revision 3. | `de-desktop-one-point.png`, CUA action record |
| DE desktop polygon editing | Explicitly staged three points; actual Terra/MapLibre overlay mounted. Native corner drag changed the outline; native midpoint drag increased the counter from 3 to 4. The first height-reference position remained visible. | `de-desktop-staged.png`, `de-desktop-after-drag.png` |
| DE desktop invalid field | A complete synthetic source/roof form with pitch 90 was refused. Pitch retained 90 and focus; other values remained. The first layout put its message far away; the repair associates the existing message immediately with the invalid input. | `de-desktop-invalid-pitch.png` before; `de-desktop-field-error-final.png` after; native DOM `pitch`, `aria-invalid=true`, `aria-describedby` resolves to the visible message |
| Native geometry service and application | Correcting pitch to 30 invoked the existing real geometry-review route and added one roof/source group to the shared project, increasing roofs 1 → 2. It did not calculate or approve an energy/equipment system. | Native checking/added states, shared object list and subsequent saved readback |
| Shared views and history | The new face appeared in the plan selector and actual 3D canvas. One native common Undo changed roof count 2 → 1 and restored the saved baseline; one Redo changed it back to 2. Initial feedback incorrectly continued to say added after Undo; the repair now says the drawing is paused/retained. | `de-desktop-scene-pre-save.png`, `de-desktop-undo-before-feedback-fix.txt`, `de-desktop-undo-final.txt` |
| Result visibility | The old success collapsed the long form while leaving the viewport at the site footer. The repaired success focused the drawing section at top 178.13 px, below the sticky bars ending at 162 px. It clearly said the roof was added to the project draft and still required Save project. | `de-desktop-success-before-feedback-fix.png`, `de-desktop-success-final.png` |
| Protected drawing and save | Closing the preview did not discard the unconfirmed drawing. After returning the shared project to its saved baseline and reloading, the four points, source declarations and corrected values could be reopened and reapplied. Native Save project then confirmed revision 4; the unfinished drawing entry retired. The English route independently reopened revision 4 with the added face present. | `en-desktop-v4-readback.txt`, native revision/status transitions |
| Whole-system identity | The shared product identity says Solution Configurator / by Linker, followed by Linker's editable-project workflow. Expanded About explains shared inputs/design, saving and restoring drafts, and common geometry. Software/data credits are subordinate. The final English page reopens saved revision 5. | `en-desktop-system-identity-final.png`, `en-desktop-v5-readback.txt` |
| EN phone partial recovery | Started a separate drawing, recorded one actual map-centre point, paused and really reloaded. The recovery entry retained exactly one point. | `en-phone-one-point.png`, `en-phone-one-point-map.png`, `en-phone-recovered-one-point.txt` |
| DE phone cross-language recovery | Switching the paused project from EN to DE retained that one-point entry. Opening it and making two real new map clicks produced three points. Explicit close opened the formal-German properties. The drawing kept its original EN decimal-point convention and showed that instruction in German. | `de-phone-recovered-and-invalid.txt` |
| DE phone field correction | A full synthetic source/roof form with pitch 90 was refused, retaining all values and focus. `scrollWidth` and `innerWidth` both read 390. The narrow two-column form was identified for repair rather than passed as readable. | `de-phone-field-error.png` before the one-column repair |
| Final DE phone single column | After native WindPress generation and restoring the customer identity, the three-point drawing and all entered values remained available. Both property grids read one 318 px column. Invalid pitch 90 retained focus and its complete associated error; document width remained 390 px. | `de-phone-field-error-final.png` |
| Native repeated success | Corrected pitch to 30, added the third roof through the real service, used common Undo to return to two roofs/revision 4, resumed without editing any field, and submitted again. The second success focused the drawing section at 210.56 px below the 204.39 px sticky bar; roof count returned to three. Save project confirmed revision 5 and retired the prepared recovery entry. | `de-phone-repeat-success-final.png`, `de-phone-repeat-success-final.txt`, native save readback |
| Native cached viewport reentry | At saved revision 5, entered actual 3D, returned to the cached map, then reopened cached 3D within the same running app. Both entries completed and the three roof faces rendered. | `de-phone-scene-reentry-final.png`, `de-phone-v5-and-reentry.txt` |

## Source pins and native styling

The earliest one-point screenshot uses source pin `9efd14fc`. The initial staged/drag/form-failure screenshots use `02c87049`; the associated desktop field error and first 3D view use `b48ffda6`. Final desktop success/history feedback uses `786d0db9`. The repeated-success counter repair is `726e326b`; its independent real-component probe and final native phone path both cover unchanged resubmission after Undo/Resume. The EN identity, EN phone and initial DE phone captures use that JavaScript build.

The final style-only pin is `716ae5f456377339f5b41b85430fbb3e92e0ea67`. Its one-column override is confined to the drawing property grid at widths ≤640 px; it changes no JavaScript, locale or application build. Source CSS and the existing p548 WindPress volume both hash to `6dadc4a210a067a8a831ef3834f3c28912f6d096ac1cb188145df99b998e2bb2`.

The native WindPress Performance → Generate action completed at the UI-displayed `2026-10-24 03:07:50`, cache 836.15 kB; see `windpress-native-generation.txt`. This is the existing WordPress/WindPress pipeline. The customer identity was restored after this administrative generation; no alternative CSS builder or new instance was introduced.

The final phone field-error, repeated-success and cached-3D captures use this generated CSS. The new style rule changes only the phone grid; the earlier desktop layout remains unaffected by its media query.

## Acceptance boundary

The street-map consent control was not activated in these paths. Provider replacement/consent, actual touch gestures, all failure states at all four language/viewport combinations, production and engineering/equipment/calculation/report/site consumers are not granted acceptance here. The full matrix remains open.

An attempted self-crossing corner drag did not establish a native invalid-geometry service response: the library retained a valid edited outline and the service accepted that outline. That attempt is not a backend-refusal proof. The real component fixture does exercise explicit geometry refusals, independently from this native boundary.

Native raw scope/identity behavior is supplemented by real hook/journal tests and independent fault probes. Reading a rendered recovery entry or seeing it retire does not replace their exact-byte CAS, delayed-owner or prepared-payload assertions.
