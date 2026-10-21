# #484 + #485 the finishing click and the joined status line

2026-10-21. Local snapshot instance only (w480, restarted from this checkout): WordPress 7.1.3, snapshot `20261021-1023`, local engine at `http://127.0.0.1:9253`, build `configurator.js?ver=1a10470462d9176838fa`. No merge, no deploy, no production write, no registration, no inquiry; the save is a guest save on the local instance. Harness: `walk.mjs` (real pointer clicks on the map, real guest save). Record: `record.json`. Screenshots: `shots/`.

## #484 the click that closes a drawn plane

Before (the #480 walk, `docs/acceptance/2026-10-21/480/` on the #480 branch): TerraDraw 1.35.0 closes the polygon inside its canvas `pointerup` listener (`base.adapter.ts` pointerup → the mode's `onClick` → `close` → `finish`); the app's `finish` handler set the mode `static`; MapLibre then reported the same gesture as a click (`MapMouseEvent.originalEvent`, dispatched after pointerup), the `getMode() === 'polygon'` guard missed it, and `/roof/outline` replaced the drawn plane. The refusal sentence was overwritten the same way.

The fix in `RoofStep.tsx`: a capture `pointerup` listener on the map canvas records the gesture before the adapter's listener runs; the `finish` handler keeps that pointerup, and the map click listener drops a click within 500 ms and 2 px of it (the app's capture listener is registered at map mount, before `terra.start()`; both bind to `map.getCanvas()`). Every other click is a selection.

After, all four EN/DE × 1440/390 runs, selecting Triftstraße 5 first:

| | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Selection | `/roof/outline 200`, 16 planes, 14 modules, 6.44 kWp | same | `Amtliches Gebäudemodell: Triftstraße 5` | same |
| Closing click | `/roof/pack 200`, **no** `/roof/outline` | same | same | same |
| Status after closing | “The plane you drew is in the list.” | same | “Die gezeichnete Fläche steht in der Liste.” | same |
| Planes | 16 → 17 | 16 → 17 | 16 → 17 | 16 → 17 |
| Total | 14 modules, 6.44 kWp → 15 modules, 6.9 kWp | → 16 modules, 7.36 kWp | → 15 Module, 6,9 kWp | → 16 Module, 7,36 kWp |
| A new click on the roof | third request `/roof/outline 200` | same | same | same |

The plane over `MAX_DRAWN_PLANE_M2 = 3000` (EN 1440 and DE 1440, after zooming out): `/roof/pack 422`; the refusal sentence stays after the closing click (“Draw the plane on one roof: this one is too large or outside Germany.” / “Zeichnen Sie die Fläche auf einem einzelnen Dach ein: Diese ist zu groß oder liegt außerhalb Deutschlands.”); the 16 selected planes and 14 modules, 6.44 kWp are unchanged and no `/roof/outline` follows the closing click.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Drawn plane in the list | [shot](shots/484-drawn-en-1440.png) · [total](shots/484-drawn-en-1440-total.png) | [shot](shots/484-drawn-en-390.png) · [total](shots/484-drawn-en-390-total.png) | [shot](shots/484-drawn-de-1440.png) · [total](shots/484-drawn-de-1440-total.png) | [shot](shots/484-drawn-de-390.png) · [total](shots/484-drawn-de-390-total.png) |
| Refused plane, sentence stays | [shot](shots/484-refused-en-1440.png) | — | [shot](shots/484-refused-de-1440.png) | — |

The primary shot shows the status sentence and the list; the `-total` shot shows the appended “Facing south, tilt 35°” row (checked) and the increased total.

## #485 the add result and the save result

Before (the #479 walk, `record.json` `rows.C30.guest.*.action.text`): `All products are in your solution draft.Saved to your account. Open saved solution` / `Alle Produkte sind in Ihrem Lösungsentwurf.In Ihrem Konto gespeichert. Gespeicherte Lösung öffnen`.

After, the same flow (calculate, Add all, Save solution, guest):

| | 1440 | 390 |
| --- | --- | --- |
| EN | [“All products are in your solution draft. Saved to your account. Open saved solution”](shots/485-en-1440.png) | [same](shots/485-en-390.png) |
| DE | [“Alle Produkte sind in Ihrem Lösungsentwurf. In Ihrem Konto gespeichert. Gespeicherte Lösung öffnen”](shots/485-de-1440.png) | [same](shots/485-de-390.png) |

The status line now separates the add sentence and the saved sentence with one space; no copy changed. `App.test.tsx` also covers the failed-save combination in both languages (`All products are in your solution draft. The solution could not be saved. Try again.` / `Alle Produkte sind in Ihrem Lösungsentwurf. Die Lösung konnte nicht gespeichert werden. Versuchen Sie es erneut.`) and asserts the exact `textContent`.
