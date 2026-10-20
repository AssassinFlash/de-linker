# #458 open_configurator acceptance

2026-10-21. Records only. No URL change, no copy change, no service change.

The walk is the #445 matrix, not a new session. Local instance `m445` (`http://127.0.0.1:9231`). Production is page GET and `GET linker/size-hint`. No production Genie turn, no account, no mail.

## Rule

#393: `linker/size-hint` accepts `lang`. `SizeHint::execute()` drops it. `lang` is not a configurator field. A German sizing turn therefore opens the English configurator until a new ruling replaces #393. The query still contains only fields the customer stated (#365).

Direct `/de/loesungskonfigurator/` is German. The configurator's language follows that page, not the size-hint query.

Do not emit `/de/loesungskonfigurator/` from size-hint, and do not write `lang` into the query, without a new ruling. The matrix harness marked the four German `open_configurator` cells fail because it expected `/de/loesungskonfigurator/` and `html lang=de`. That expectation is the missing record, not a defect. Acceptance verdict for those four cells is pass under #393.

`SizeHintTest::test_a_german_hint_drops_lang_and_keeps_the_english_path` fails if `execute()` stops dropping `lang` or stops returning the English path. That failure is the route to a ruling, not a silent ship.

Empty fields on this URL (postcode, annual, kWp empty; backup `none`; phase `3` is the form default) are #457. This record does not accept that miss.

## What was opened

Local Genie prompts (`matrix/harness.mjs`):

- EN: `Residential site with 10 kWp PV and 4500 kWh per year, three-phase, postcode 80538, backup needed.`
- DE: `Wohngebäude mit 10 kWp PV und 4500 kWh im Jahr, dreiphasig, PLZ 80538, Notstrom benötigt.`

`open_configurator` was followed for guest and approved, EN and DE, at 1440×900 and 390×844. Both engines' ability GET with `input[lang]=de` returns the English path and no `lang` query:

`/solution-configurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538`

Configurator bundle on both engines: `configurator.js?ver=e90a705b79f5bc1bc010`, sha256 `277692b3f931595049f493c636feca4006a6b7978448384532892ae14c839143`.

Shot paths below are relative to `docs/research/2026-10-21-configurator-rooftop/matrix/`.

## Four passing open_configurator cells

English entry. Three-step rail mounts. Header language control sits on EN.

The four local landing shots are two images. Guest and approved opened the same URL, so the approved file matches the guest file byte for byte. Production page GET of that URL (`shots/prod-size-hint-url-1440.png`, `shots/prod-size-hint-url-390.png`) is the same two images. No approved production session was opened; the production column is the page GET.

| Cell | Screenshot | Result |
| --- | --- | --- |
| guest · en · 1440 | [`shots/l2-guest-en-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/l2-guest-en-1440.png) | Pass. English rail: 01 Inputs / 02 Solution / 03 Design report. Title Solution Configurator. App mounted. `html lang=en-US`. |
| guest · en · 390 | [`shots/l2-guest-en-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/l2-guest-en-390.png) | Pass. Same English rail, stacked. Header EN. `html lang=en-US`. |
| approved · en · 1440 | [`shots/l2-approved-en-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/l2-approved-en-1440.png) | Pass. Same landing as guest EN 1440 (sha256 `915c9621c695`). Production: page GET, same rail. No approved production session. |
| approved · en · 390 | [`shots/l2-approved-en-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/l2-approved-en-390.png) | Pass. Same landing as guest EN 390 (sha256 `f88935dd4487`). Production: page GET, same rail. No approved production session. |

Production English page GET, same URL, cookie banner still up, rail still English: [`shots/both-prod-prefill-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/both-prod-prefill-1440.png), [`shots/both-prod-prefill-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/both-prod-prefill-390.png). Local twins are byte-identical (`both-engines.json` cases `prefill`). DOM: `html lang=en-US`, title Configure a Storage System, steps 01Inputs / 02Solution / 03Design report, mounted.

## Four German-URL cells

German Genie turn. These are the four German-URL cells of the open_configurator link: guest and approved, 1440 and 390. Production is the other engine, under the table. The link is the English path. Accepted under #393. Harness verdict was fail; that verdict is the record gap.

These four shots are the same two images as the passing cells. A German turn did not open a different page.

| Cell | Screenshot | Result |
| --- | --- | --- |
| guest · de · 1440 | [`shots/l2-guest-de-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/l2-guest-de-1440.png) | Accepted (#393). Landed `/solution-configurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538`, not `/de/loesungskonfigurator/`. English rail. `html lang=en-US`. Header EN. |
| guest · de · 390 | [`shots/l2-guest-de-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/l2-guest-de-390.png) | Accepted (#393). Same English page at 390. Header EN. `html lang=en-US`. |
| approved · de · 1440 | [`shots/l2-approved-de-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/l2-approved-de-1440.png) | Accepted (#393). Same English URL as guest DE. sha256 `915c9621c695`. No approved production session. |
| approved · de · 390 | [`shots/l2-approved-de-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/l2-approved-de-390.png) | Accepted (#393). Same English page at 390. sha256 `f88935dd4487`. No approved production session. |

Production, both engines, same input including `lang=de` (`production-smoke.json` `size-hint-ability`, HTTP 200):

- local `configurator_url`: `http://127.0.0.1:9231/solution-configurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538`
- production `configurator_url`: `https://de-linker.com/solution-configurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538`

No `lang` in either query. Opening the production URL: [`shots/prod-size-hint-url-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/prod-size-hint-url-1440.png), [`shots/prod-size-hint-url-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/prod-size-hint-url-390.png). English rail, `html lang=en-US`, title Solution Configurator, mounted. Same bytes as the local German landings.

## Direct German URL

Both engines, 1440 and 390. This is the German page. It is not what size-hint returns.

`both-engines.json` case `prefill-de`. Requested path `/de/loesungskonfigurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538`. Status 200. `html lang=de-DE`. Title Lösungskonfigurator. Steps 01Eingaben / 02Lösung / 03Auslegungsbericht. Mounted. Local and production shots of this case match byte for byte.

| Engine | Viewport | Screenshot | Result |
| --- | --- | --- | --- |
| local | 1440 | [`shots/both-local-prefill-de-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/both-local-prefill-de-1440.png) | German. Lösungskonfigurator, 01 Eingaben / 02 Lösung / 03 Auslegungsbericht. Header DE. Cookie banner in German. |
| local | 390 | [`shots/both-local-prefill-de-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/both-local-prefill-de-390.png) | German. Same rail, stacked. Header DE. Cookie banner in German. |
| production | 1440 | [`shots/both-prod-prefill-de-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/both-prod-prefill-de-1440.png) | German. Same page as local 1440 (sha256 `c0c6a18a7ebf`). Header DE. |
| production | 390 | [`shots/both-prod-prefill-de-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/both-prod-prefill-de-390.png) | German. Same page as local 390 (sha256 `1e22612afb0f`). Header DE. |

Cookie dismissed, production only (`production-smoke.json` `cfg-de`, path `/de/loesungskonfigurator/?pv_kwp=10&annual_kwh=4500&phase=3&plz=80538`): [`shots/prod-cfg-de-1440.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/prod-cfg-de-1440.png), [`shots/prod-cfg-de-390.png`](../../../research/2026-10-21-configurator-rooftop/matrix/shots/prod-cfg-de-390.png). `html lang=de-DE`, title Lösungskonfigurator, steps 01Eingaben / 02Lösung / 03Auslegungsbericht, mounted. Header DE.

## Sources

- [`matrix/matrix.md`](../../../research/2026-10-21-configurator-rooftop/matrix/matrix.md) — open_configurator section. Class of the four German cells: 验收记录缺口. #458.
- [`matrix/rows.json`](../../../research/2026-10-21-configurator-rooftop/matrix/rows.json) — eight `open_configurator` rows. Harness `verdict` on the German rows is `fail`. This record supersedes that verdict with the #393 acceptance. It does not rewrite `rows.json`.
- [`matrix/production-smoke.json`](../../../research/2026-10-21-configurator-rooftop/matrix/production-smoke.json) — `size-hint-ability`, `size-hint-url`, `cfg-de`.
- [`matrix/both-engines.json`](../../../research/2026-10-21-configurator-rooftop/matrix/both-engines.json) — cases `prefill` and `prefill-de`.
- Fixture that already locks the English path: `services/genie/tests/fixtures/size-hint-urls.json`.
