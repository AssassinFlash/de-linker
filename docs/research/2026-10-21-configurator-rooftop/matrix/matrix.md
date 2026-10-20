# Genie ↔ Configurator matrix (#445)

Local instance `m445` (`http://127.0.0.1:9231`, engine `9232`, Genie `9233`), snapshot `20261019-1715` (taken 2026-10-19T09:18:02+00:00).

Production, this pass: guest Store API cart writes for products 3556 and 3611, read back, two guest Genie turns, then the lines removed. No account. No mail. No contact or inquiry card. Pending and approved production sessions were not opened.

Cell verdicts are what the matrix measured. They are not, by themselves, functional defects. Each miss is classed after the same check on both engines, except where a production session could not be opened:

- 功能缺失
- 行为损坏（本地与线上不一致时以线上为准，先查版本差）
- 集成接口断点（工具各自正常，链路参数没接上）
- 验收记录缺口（行为正确只是没记录）
- 本地实测·线上待测（该状态在线上没有打开会话）

No cell is 功能缺失. Configurator bundle on both engines is the same file: `configurator.js?ver=e90a705b79f5bc1bc010`, 208659 bytes, sha256 `277692b3f931595049f493c636feca4006a6b7978448384532892ae14c839143`. It contains `openRoof` and does not contain `URLSearchParams`.

| Link | Pass | Fail | Class of the miss | Tickets |
| --- | ---: | ---: | --- | --- |
| size-hint prefill | 0 | 8 | 集成接口断点 | #457 |
| open_configurator landing | 4 | 4 | 验收记录缺口 | #458 |
| design → add all → Genie on the draft | 0 | 12 | 访客 4 格集成接口断点；待审与已批 8 格本地实测·线上待测 | #459 pending-evidence，不是 P1 |
| Total of the three links | 4 | 24 | | |

`?step=roof` is not one of those 28 cells. Spec 12's accepted check (retired URL 301 onto `?step=roof` in one hop) passed on both engines. The closed canvas is not that check. It is a design item, #462, with no bug label.

Price gate: held on every local draft cell, and on the two production guest turns. No amount on guest or pending locally. Approved draft locally shows net prices. No P0. Production pending and approved price gates were not exercised.

`rows.json` has a `class` field on every cell.

## size-hint

Class: 集成接口断点. Both engines. #457 stands.

Genie and `linker/size-hint` emit the stated fields. The configurator does not read them. `phase=3` on the form is the default, not a prefill. Guest and approved match on the local Genie turn. Units were not applied because the values were not written; no wrong-unit conversion was seen.

The production equivalent is `GET linker/size-hint` with `input[lang]=de`, then opening that URL. Local and production both return the English path with `pv_kwp=10`, `annual_kwh=4500`, `phase=3`, `backup=needed`, `plz=80538`, and no `lang`. Opening it leaves plz, annual and kWp empty and backup `none` on both engines, 1440 and 390.

Precedent for a later fix: `SizeHint::execute` already builds those query keys (`plugins/linker-commerce/includes/Abilities/SizeHint.php`, fixture `services/genie/tests/fixtures/size-hint-urls.json`). `readConfig` only reads `element.dataset.step`. `Mount.php` does not copy the query onto the mount. Connect the existing keys to the existing form defaults. Do not invent a new field set.

| State | Lang | 1440 | 390 | Local | Production | Class |
| --- | --- | --- | --- | --- | --- | --- |
| guest | en | fail | fail | fields empty | same URL, fields empty | 集成接口断点 |
| guest | de | fail | fail | English path, fields empty | ability returns the English path; German page with the same fields also leaves kWp empty | 集成接口断点 |
| approved | en | fail | fail | fields empty | same as guest; no approved production session | 集成接口断点 |
| approved | de | fail | fail | English path, fields empty | same as guest DE | 集成接口断点 |

Evidence: `shots/l1-guest-en-1440-configurator.png`, `shots/both-prod-prefill-1440.png`, `shots/both-prod-prefill-de-1440.png`.

## open_configurator

English lands on the three-step rail (Inputs / Solution / Design report) and the app mounts, locally and on production (page GET). Those four cells are pass.

German Genie turns open that same English page (`html lang=en-US`), not `/de/loesungskonfigurator/`. Class: 验收记录缺口. #458 stands. Not a broken page, and not a local/production split.

`#393` accepted `lang` on size-hint and then ignored it: it is not a configurator field, and the prefill still contains only fields the customer stated. The fixture locks the English path. Both engines' ability GET with `input[lang]=de` return that English path. A direct visit to `/de/loesungskonfigurator/` is German on both (`html lang=de-DE`, title Lösungskonfigurator, steps 01Eingaben / 02Lösung / 03Auslegungsbericht).

A later change that emits `/de/loesungskonfigurator/` would contradict `#393` and the fixture.

| State | Lang | 1440 | 390 | Local | Production | Class |
| --- | --- | --- | --- | --- | --- | --- |
| guest | en | pass | pass | three-step rail | page GET, same rail | pass |
| guest | de | fail | fail | English path | ability URL is the English path; German page itself is German | 验收记录缺口 |
| approved | en | pass | pass | three-step rail | page GET, same rail; no approved session | pass |
| approved | de | fail | fail | English path | same ability URL as guest DE | 验收记录缺口 |

## Draft

Cell verdict is fail because Genie does not state the quantity. Add-all and the price gate are not misses.

Passed, all six local state × language cells:

- Design status `solution` for PLZ 80538, 4500 kWh/year, 10 kWp, three-phase, backup `none` (spec 14).
- Add all. Confirmation: “All products are in your solution draft.” / “Alle Produkte sind in Ihrem Lösungsentwurf.”
- Draft lines: qty 1 of GW10K-ETA-G20 (3556) and qty 1 of GW6.0-BAT-D-G20 (3611).

Price gate held locally:

- Guest: “Log in for prices” / “Preise nach Anmeldung”. No amount.
- Pending: “Account under review. Prices after approval.” / “Ihr Konto wird geprüft. Preise nach Freigabe.” No amount.
- Approved: €1,090.00 and €1,430.00 (German format 1.090,00 € and 1.430,00 €).

### Production guest

2026-10-20T18:16Z. Public Store API, then a Genie turn on the cart page, then the lines removed. Harness: `production-draft.mjs`. Record: `production-draft.json`. No mail.

| Lang | Page | Cart read-back | Genie | Amount |
| --- | --- | --- | --- | --- |
| en | `/cart/` | add-item 201; after reload, qty 1 of 3556 and 3611 | names both; “shows no separate quantity count per line, so I cannot confirm quantities from here.” Conversation 7897 | none; “Net price after partner sign-in” |
| de | `/de/loesungsentwurf/` | same, a second guest session | names both; “Wie viel je Produkt im Entwurf liegt, zeigt die Bestätigungskarte beim Senden der Anfrage.” Conversation 7898 | none; “Nettopreis nach Partner-Anmeldung” |

Both sessions then `remove-item` 200, remaining 0. 1440 and 390 screenshots are the same turn, resized: `shots/prod-draft-guest-<lang>-1440.png`, `shots/prod-draft-guest-<lang>-390.png`, and the `genie` pair.

The “12 pcs” / “12 Stück” sentence is a pairing-document citation, not the draft line quantity. Genie did not state 1 and did not invent 1.

Class of the four guest cells: 集成接口断点. Same miss on both engines. Not 行为损坏.

The reader is unchanged: `PageContext::draft_ids()` passes English ids only. `page.py` `_draft()` stores `product_id` and `title` only. Spec 13 page perception for a draft is those ids via Store API `include`. The same cart already exposes quantity to handoff (`wc_load_cart()`: name, SKU, quantity). The seam is that the reader used for the answer does not receive the quantity the cart already has.

Store API `include=3556,3611` bodies, local and production, EN and DE: `store-api/`. Both engines return both products. Guest `prices` is null in those bodies.

### Pending and approved

Local result stands: quantity not stated, price gate held. Production sessions for those two states were not opened. Opening one would need a customer-account read or a registration, and registration sends mail. Neither was done.

Those eight cells are 本地实测·线上待测. #459 is pending-evidence, not P1. The guest reproduction is recorded on the ticket so it is not lost; the ticket does not claim the unprobed states.

| State | Lang | 1440 | 390 | Local | Production | Class |
| --- | --- | --- | --- | --- | --- | --- |
| guest | en | fail | fail | qty not stated; gate held | qty not stated; no amount; cart qty 1 read back | 集成接口断点 |
| guest | de | fail | fail | qty not stated; gate held | qty not stated; no amount; cart qty 1 read back | 集成接口断点 |
| pending | en | fail | fail | qty not stated; gate held | not probed | 本地实测·线上待测 |
| pending | de | fail | fail | qty not stated; gate held | not probed | 本地实测·线上待测 |
| approved | en | fail | fail | qty not stated; net prices on the draft | not probed | 本地实测·线上待测 |
| approved | de | fail | fail | qty not stated; net prices on the draft and in the card DOM | not probed | 本地实测·线上待测 |

Add-all shots: `shots/l3-<state>-<lang>-solution.png`.

Pending EN and approved EN local screenshots show “Genie could not load this product.” That string is the card's unloaded state (`GenieCard` renders it while `product` is still null). Approved DE cards then showed the net prices. Not filed as its own defect. Logged-in DE panels also restored an earlier English thread; that reuse is not a product bug.

A run that selected backup `needed` without a load and hours returned no candidate. The configurator stated that. That run is not a product failure and is not in `rows.json`.

## `?step=roof`

Not a defect. Class of the earlier “closed canvas” reading: 验收记录缺口, plus a new-interface design item. #462 was rewritten as that design item. The bug label is off.

Spec 12's accepted check is that a retired URL 301s onto `?step=roof` in one hop, then the page is 200. That check passed on both engines. Status and Location, recorded without following the redirect (`redirects-301.json`, also `both-engines.json` case `redirect-301`):

| Engine | From | Status | Location |
| --- | --- | ---: | --- |
| local | `/design-canvas/` | 301 | `http://127.0.0.1:9231/solution-configurator/?step=roof` |
| local | `/de/design-canvas/` | 301 | `http://127.0.0.1:9231/de/loesungskonfigurator/?step=roof` |
| local | `/de/entwurfsflache/` | 301 | `http://127.0.0.1:9231/de/loesungskonfigurator/?step=roof` |
| production | `/design-canvas/` | 301 | `https://de-linker.com/solution-configurator/?step=roof` |
| production | `/de/design-canvas/` | 301 | `https://de-linker.com/de/loesungskonfigurator/?step=roof` |
| production | `/de/entwurfsflache/` | 301 | `https://de-linker.com/de/loesungskonfigurator/?step=roof` |

After the hop the query is kept and `.linker-roof` is absent, EN and DE, 1440 and 390, both engines. `data-step` is absent on the mount. That is not a failed redirect.

The closed canvas is the component gate. `config.ts` sets `openRoof` only when the mount has `data-step="roof"`. `Mount.php` does not set it. `ResidentialPanel.tsx` lines 126–130 open the step only when `config.openRoof && defaults?.plz`. `App.tsx` renders `ResidentialPanel` with `config`, `engine`, and `store`. It does not pass `defaults`. A local injection of `data-step="roof"` (browser fulfill only, not product code, not on production) left the canvas closed and the postcode empty.

Wiring `step` to `openRoof`, and focusing the postcode when the query has none, is not an existing interface. No precedent was found for opening the roof canvas from the query alone. The established path is the button: `ResidentialForm.openRoof` validates `plz` and, if empty, `setFocus('plz')`. A later change needs its own design justification. It is not a bug fix.

The roof step itself opens from that button. Local, postcode 80538, “No PV figure yet? Estimate from the roof”. The credit is the DOM text, not the screenshot alone: `both-engines.json` `roof-button` `roofText` is `© Bayerische Vermessungsverwaltung – www.geodaten.bayern.de, CC BY 4.0`. The shot was retaken at 2026-10-20T18:20:57Z after the consent accept (`shots/both-local-roof-button-1440.png`). The earlier file had the cookie banner over that line. Production was not clicked; it serves the same bundle and shows the same button (“Noch keine PV-Leistung? Aus dem Dach abschätzen” on the German page).

### Retired 390 shots

`both-local-retired-de-390.png` and `both-prod-retired-de-390.png` are both 390×844. Difference: 23 pixels, bbox (172, 17, 213, 63), channel delta at most 1. The English 390 pair has the same bbox and the same bound. The German 1440 pair is identical. That is a header-crop residual, not a layout or behavior split. The shots were not retaken. Record: `retired-390-diff.json`.

## Local feed

Class: 行为损坏. #460 stands. Production is the authority. Same compatibility hash, so this is not a tool-version split.

The 17:34 stamps in the previous write-up were recollection and were already stale. This table is the saved bodies. Fetch time and sha256 are in `feeds/feed-snapshot.json`, recorded with the bytes, not after the fact.

| Engine | Fetched | sha256 | `generated_at` inside the body | Products | With figures | Citation hosts |
| --- | --- | --- | --- | --- | ---: | --- |
| local | 2026-10-20T18:13:52.786999+00:00 | `69a770b4a9ddb0cb983d71dde082053b1f0304a933b4c5c73a8efd504d7b0543` | 2026-10-20T18:13:52+00:00 | 106 | 0 | `127.0.0.1` (210) |
| production | 2026-10-20T18:13:53.069035+00:00 | `d16633956675c6b3a639340da57e596b0abfc333aba2815a3cb02f995e8ec2ea` | 2026-10-20T18:13:58+00:00 | 106 | 83 | `de-linker.com` (210) |

Bodies: `feeds/local-engineering-feed.json`, `feeds/prod-engineering-feed.json`. Schema 1. Compatibility `81f8688f5d0383bf275607b0aaaf4367963881f1b9c4c47f0450ac7b55f980e6`.

`EngineeringFeed::is_hosted_citation()` keeps only `de-linker.com` and `www.de-linker.com`. After pull load, local citations are the instance host, so every figure is dropped and a stock local engine cannot design. Production citations pass the same allowlist. This is not a configurator logic defect.

The draft cells used the production feed file in the instance engine directory only. No product code was changed. Do not run `just serve m445` against that instance if the replacement must stay: serve rewrites the feed from the local endpoint.

## Tickets

- #457 集成接口断点, stands. Configurator ignores size-hint query fields. Both engines.
- #458 验收记录缺口, stands. German sizing opens the English configurator URL. That matches `#393` and the fixture.
- #459 pending-evidence, not P1. Guest production reproduced the quantity miss (集成接口断点). Pending and approved production turns were not run (本地实测·线上待测).
- #460 行为损坏, stands. Local engineering feed drops every figure after pull load. Production feed is the authority. Snapshot and hash are in `feeds/`.
- #462 design item, not a defect. Spec 12's 301 contract holds on both engines. Wiring `step` to `openRoof` has no existing interface. Bug label removed.

No price leak. No mail sent. No product code changed.
