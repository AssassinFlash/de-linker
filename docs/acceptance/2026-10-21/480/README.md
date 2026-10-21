# #480 the roof detail walk (R05/R06/R08/R10/R11/R13)

2026-10-21. Local snapshot instance only. No merge, no deploy, no production write, no inquiry, no registration, no mail. The walk is a guest: the configurator is public, and nothing was submitted.

Instance `w480`: `just sync w480` (WordPress `http://127.0.0.1:9252`, engine `http://127.0.0.1:9253`) with the live snapshot `20261021-1023` (taken 2026-10-21T02:26:29Z, loaded 02:27:31Z; theme, plugins and uploads). Checkout `d2d7c8fa`. Build: `configurator.js?ver=bacae88a042528100047`, sha256 `7ac9d249d7afd305f1ec0d63c7f1475aecc8d9f3efb48a29072c8ec5af5eaee5`, 209422 bytes; the lazy roof chunk `52.js` (the RoofStep code), sha256 `e348bbca25a6aab0796342354e4693c7c2c246acfd330d4834d7b0c7cc25e63e`, 9724 bytes.

Harness: `walk.mjs` (guest; real pointer clicks on the map, checkboxes, buttons and the Draw control; the consent bubble is dismissed with a DOM click as in the 473 harness). The page-level changes are a stylesheet that disables animation and sets scroll margins, a MutationObserver on the status element (ordered transitions, so a sentence that is immediately replaced is still recorded), and `visibility: hidden` on the sticky site header and step rail for element captures only. Record: `record.json`. Screenshots: `shots/`, named `<page>-<viewport>-<lang>-<state>.png` per `docs/acceptance/protocol.md`.

The external Bavarian WMS raster is not reachable from this environment (R03 recorded the same on 2026-10-15; the local CSP allows the imagery hosts), so the aerial image is grey in these shots. The outline, roof planes and module polygons are the app's own GeoJSON layers and are visible; the attribution line is present.

Fixture: PLZ 80538, Triftstraße 5 (the R04 fixture): 16 LoD2 planes — 6 usable (3 with modules 6 + 5 + 3, checked by default; 3 with 0 modules, disabled) and 10 excluded (7 steeper than 60°, 3 facing north).

## Verdicts

| Row | Behaviour | Class | Verdict |
| --- | --- | --- | --- |
| R05 | Check or uncheck a usable roof plane; the module count and kWp follow | 验收记录缺口 | **Verified** EN/DE × 1440/390 |
| R06 | Draw a plane by hand and pack it; reject a plane over 3000 m² or outside Germany | defect | **Defect #484**: the engine pack works, but the click that closes the polygon also selects a building and replaces the drawn plane; the refusal sentence is overwritten. Engine bounds verified |
| R08 | After adopting a roof: “Change roof” reopens the step; “Enter kWp instead” clears the roof and makes kWp manual again | 验收记录缺口 | **Verified** EN/DE × 1440/390 |
| R10 | An excluded plane shows its reason (north-facing / too steep) | 验收记录缺口 | **Verified** EN/DE × 1440/390 (7 × steeper than 60°, 3 × faces north) |
| R11 | Four failure states: no building, LoD2 unavailable, drawn plane refused, roof data load failure | 验收记录缺口 (3 states) + defect #484 (drawn-plane refusal) | **3 pass + 1 defect (#484)**: no building, LoD2 503 and unknown-postcode load failure pass; the drawn-plane refusal is the R06 defect #484 (sentence appears, is not stable) |
| R13 | Closing without adopting returns to the form and keeps kWp manual | 验收记录缺口 | **Verified** EN/DE × 1440/390 — closing after an in-step selection applies no roof; the form keeps manual kWp editable (`readOnly: false`) |

## R05 — a checked plane changes the totals

The first enabled checkbox, “Facing south, tilt 14° 6 modules” (“Ausrichtung Süd, Neigung 14° 6 Module” — the record's text is the UI text with whitespace collapsed), was unchecked and checked again.

| | EN | DE |
| --- | --- | --- |
| Initial | 14 modules, 6.44 kWp | 14 Module, 6,44 kWp |
| After uncheck | 8 modules, 3.68 kWp | 8 Module, 3,68 kWp |
| After recheck | 14 modules, 6.44 kWp | 14 Module, 6,44 kWp |

`record.json` `cases[*].steps.r05` has the checkbox label and all three totals.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Unchecked: 8 modules, 3.68 kWp | [1440](shots/roof-1440-en-r05-unchecked.png) | [390](shots/roof-390-en-r05-unchecked.png) | [1440](shots/roof-1440-de-r05-unchecked.png) | [390](shots/roof-390-de-r05-unchecked.png) |
| Rechecked: 14 modules, 6.44 kWp | [1440](shots/roof-1440-en-r05-rechecked.png) | [390](shots/roof-390-en-r05-rechecked.png) | [1440](shots/roof-1440-de-r05-rechecked.png) | [390](shots/roof-390-de-r05-rechecked.png) |

## R06 — drawing is broken by the finishing click; the bounds are correct

Engine probes (`record.json` `engineProbes`, `POST http://127.0.0.1:9253/roof/pack`):

| Probe | Answer |
| --- | --- |
| Valid plane in 80538 | 200, 66 modules, 30.36 kWp, 202.07 m² |
| Plane over `MAX_DRAWN_PLANE_M2 = 3000` | 422, “a drawn plane covers at most 3000 m²” |
| Plane above the box (lat 60 / lon 20) | 422, “Input should be less than or equal to 15.1” / “… 55.2” per coordinate |
| Plane below the box (lat 40 / lon 0) | 422, “Input should be greater than or equal to 5.8” / “… 47” per coordinate |
| Self-intersecting plane inside the box | 200, `usable: false`, `excluded_reason: roof_geometry`, 0 modules |

The UI does send the pack request, and the engine answers 200 with the drawn plane's modules. The status shows “The plane you drew is in the list.” / “Die gezeichnete Fläche steht in der Liste.”

The click that closes the polygon also goes to MapLibre's click handler. TerraDraw's `finish` handler has already switched the mode to `static`, so the guard misses it and a second `POST /roof/outline` selects the building under the finishing click. In both recorded runs the outline answer landed last and the drawn plane was thrown away; the final list and total are the building's. The two answers race, so an order in which the pack lands last would leave the drawn plane appended to the building's planes — either way a building the user did not mean to select is in the list.

| | EN | DE |
| --- | --- | --- |
| `roof/pack` | 200, 20 modules | 200, 20 modules |
| `roof/outline` after the finish click | 200, a 1-plane building, 0 modules | 200, Triftstraße 9, 4 planes, 82 modules |
| Final list | the building's plane; the drawn plane is gone | the building's 4 planes, 82 modules, 37.72 kWp; the drawn plane is gone |

The same happens for the refusal: a rectangle beyond 3000 m² gets `pack` 422, the refusal sentence is set (“Draw the plane on one roof: this one is too large or outside Germany.” / “Zeichnen Sie die Fläche auf einem einzelnen Dach ein: Diese ist zu groß oder liegt außerhalb Deutschlands.”), and the outline answer then replaces it. The final state is a 32-plane building (204 modules, 93.84 kWp read back from the status total) in both languages. The ordered status transitions are in `record.json` `cases[*].steps.r06.statuses` and `.refused.statuses`; `.refused.status` and the screenshot show the final replacement. The outside-Germany branch is engine-probed only (the ticket routes hand-drawing through the local engine `/roof/pack`); both 422s share the same `invalid → refused` branch.

Defect ticket **#484** has the cause (`RoofStep.tsx` map click listener) and the fix direction. No code change in this walk.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| After drawing (a building replaced the plane) | [1440](shots/roof-1440-en-r06-drawn-attempt.png) | [390](shots/roof-390-en-r06-drawn-attempt.png) | [1440](shots/roof-1440-de-r06-drawn-attempt.png) | [390](shots/roof-390-de-r06-drawn-attempt.png) |
| After the over-limit draw (a 32-plane building) | [1440](shots/roof-1440-en-r06-refused-attempt.png) | [390](shots/roof-390-en-r06-refused-attempt.png) | [1440](shots/roof-1440-de-r06-refused-attempt.png) | [390](shots/roof-390-de-r06-refused-attempt.png) |

## R08 — change the roof, or enter kWp instead

After “Use this roof” (“Dieses Dach übernehmen”):

- Summary: “From the roof: 14 modules on 3 planes, 6.44 kWp. Triftstraße 5” / “Aus dem Dach: 14 Module auf 3 Flächen, 6,44 kWp. Triftstraße 5”.
- `#linker-kwp` = `6.44` / `6,44`, read-only.

“Change roof” (“Dach ändern”) reopens the roof step at PLZ 80538 with “Click the roof of the building in the aerial image.” / “Klicken Sie im Luftbild auf das Dach des Gebäudes.” Closing it keeps the applied roof (summary and read-only kWp unchanged).

“Enter kWp instead” (“Stattdessen kWp eingeben”) clears the roof: the summary becomes the open-roof button (“No PV figure yet? Estimate from the roof” / “Noch keine PV-Leistung? Aus dem Dach abschätzen”), and `#linker-kwp` is editable (`readOnly: false`) with the roof's value kept as the starting number. Manual means editable, not blank.

`record.json` `cases[*].steps.r08`.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Applied | [1440](shots/roof-1440-en-r08-applied.png) | [390](shots/roof-390-en-r08-applied.png) | [1440](shots/roof-1440-de-r08-applied.png) | [390](shots/roof-390-de-r08-applied.png) |
| Change roof reopened | [1440](shots/roof-1440-en-r08-change-roof.png) | [390](shots/roof-390-en-r08-change-roof.png) | [1440](shots/roof-1440-de-r08-change-roof.png) | [390](shots/roof-390-de-r08-change-roof.png) |
| Enter kWp instead | [1440](shots/roof-1440-en-r08-manual.png) | [390](shots/roof-390-en-r08-manual.png) | [1440](shots/roof-1440-de-r08-manual.png) | [390](shots/roof-390-de-r08-manual.png) |

## R10 — excluded planes show their reason

The 16-plane list has 10 excluded planes: 7 show “steeper than 60°” / “steiler als 60°” and 3 show “faces north” / “nach Norden ausgerichtet”. The other 6 are usable: 3 with modules (6, 5 and 3) are checked; 3 with 0 modules are shown but disabled. All 16 rows are in `record.json` `cases[*].steps.baseline.planes`; `steps.r10` keeps the excluded rows and the north/steep subsets.

The fixture has no LoD2 `roof_geometry` plane, so the third sentence (“outline cannot be used”) was not exercised through the map. The engine branch is probed with a self-intersecting drawn polygon: 200, `excluded_reason: roof_geometry` (`engineProbes.packGeometry`). It is the same `exclusionText` mapping.

The ticket's (and `docs/research/2026-10-21-configurator-rooftop/inventory.md:180`'s) “flat roof” wording has no exclusion behind it: `geometry.ts` has no flat-roof sentence, and the engine treats planes below `ROOF_FLAT_TILT_DEG = 10°` (`services/engine/src/linker_engine/rules.py:286-288`) as usable flat roofs whose rows face south (`roof/packing.py:34-49`, `ROOF_ASSUMPTIONS` in `roof/service.py:32-38`). The three reason sentences in `exclusionText` are north, steeper than 60°, and outline cannot be used. This walk records that as the implementation's behaviour; it is not a defect ticket.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Plane list with reasons | [1440](shots/roof-1440-en-r10-excluded.png) | [390](shots/roof-390-en-r10-excluded.png) | [1440](shots/roof-1440-de-r10-excluded.png) | [390](shots/roof-390-de-r10-excluded.png) |
| Full list (element) | [1440](shots/roof-1440-en-r10-excluded-panel.png) | [390](shots/roof-390-en-r10-excluded-panel.png) | [1440](shots/roof-1440-de-r10-excluded-panel.png) | [390](shots/roof-390-de-r10-excluded-panel.png) |

## R11 — the four failure states

| State | How it was reached | Sentence (EN / DE) | Result |
| --- | --- | --- | --- |
| No building | Click an empty point in the 80538 map | “No building at this point. Click on a roof, or draw the plane yourself.” / “An dieser Stelle steht kein Gebäude. Klicken Sie auf ein Dach oder zeichnen Sie die Fläche selbst.” | Pass |
| LoD2 unavailable | PLZ 06108 (Sachsen-Anhalt is a portal workflow), click the map; engine 503 `lod2_unavailable` | “No official building model is available here. Draw the roof plane yourself.” / “Hier ist kein amtliches Gebäudemodell verfügbar. Zeichnen Sie die Dachfläche selbst.” | Pass |
| Drawn plane refused | A rectangle beyond 3000 m²; engine 422 | “Draw the plane on one roof: this one is too large or outside Germany.” / “Zeichnen Sie die Fläche auf einem einzelnen Dach ein: Diese ist zu groß oder liegt außerhalb Deutschlands.” | Sentence appears but is replaced by the outline; **#484** |
| Roof data load failure | PLZ 99999; `/geo/plz` 404 `unknown_plz`; no map is built | “The roof could not be loaded. Try again.” / “Das Dach konnte nicht geladen werden. Versuchen Sie es erneut.” | Pass |

The fourth state is the component's `error` state. It is reached when the postcode/place load fails; MapLibre itself has no error handler (`RoofStep.tsx` has no `map.on('error')`), so a tile or style failure does not set this sentence. The walk records the reachable load-failure trigger and its sentence; whether tile errors also need the sentence is not decided by this walk. The screenshot files keep the harness state name `r11-map-error`; that state is this postcode/place-load failure, not a MapLibre tile or style error.

The drawn-plane-refused state has no stable screenshot of its own: its post-state is the R06 refused pair above (`roof-*-r06-refused-attempt.png`), where the sentence is in the ordered `record.json` trace and the final list is the building's.

`record.json` `cases[*].steps.r11`; the refusal transitions are `cases[*].steps.r06.refused.statuses`.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| No building | [1440](shots/roof-1440-en-r11-no-building.png) | [390](shots/roof-390-en-r11-no-building.png) | [1440](shots/roof-1440-de-r11-no-building.png) | [390](shots/roof-390-de-r11-no-building.png) |
| LoD2 unavailable | [1440](shots/roof-1440-en-r11-lod2-unavailable.png) | [390](shots/roof-390-en-r11-lod2-unavailable.png) | [1440](shots/roof-1440-de-r11-lod2-unavailable.png) | [390](shots/roof-390-de-r11-lod2-unavailable.png) |
| Roof data load failure | [1440](shots/roof-1440-en-r11-map-error.png) | [390](shots/roof-390-en-r11-map-error.png) | [1440](shots/roof-1440-de-r11-map-error.png) | [390](shots/roof-390-de-r11-map-error.png) |

## R13 — close without adopting

After R08's “Enter kWp instead”, the roof step was opened again and Triftstraße 5 was selected in it (14 modules, 6.44 kWp / 14 Module, 6,44 kWp), then closed with “Close roof step” (“Dachauswahl schließen”) without applying. The form is unchanged: the summary is the open-roof button, `#linker-kwp` is `6.44` / `6,44` and editable (`readOnly: false`), and no roof summary appears. The in-step selection was not applied: no roof is adopted, and the manual kWp stays editable. `record.json` `cases[*].steps.r13`.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Back in the form | [1440](shots/roof-1440-en-r13-closed.png) | [390](shots/roof-390-en-r13-closed.png) | [1440](shots/roof-1440-de-r13-closed.png) | [390](shots/roof-390-de-r13-closed.png) |

## Writes and cleanup

Guest only, no login, no calculation, no draft, no inquiry, no registration, no mail. `record.json` `writes.posts` lists every POST the page made in both cases; they are the roof step's `/wp-json/linker-ai/v1/engine/roof/outline` and `/roof/pack` calls (the engine is reached through the site's proxy) and nothing else. No Store API or `linker/v1` write was made. The instance is left running for review.
