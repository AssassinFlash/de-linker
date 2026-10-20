# Genie ↔ Configurator matrix (#445)

Local instance `m445` (`http://127.0.0.1:9231`, engine `9232`, Genie `9233`), snapshot `20261019-1715` (taken 2026-10-19T09:18:02+00:00). Production calls are GET only: no turn, no add-to-draft, no account, no mail.

Cell verdicts below are what the matrix measured. They are not, by themselves, functional defects. Each miss is classed after the same check on both engines:

- 功能缺失
- 行为损坏（本地与线上不一致时以线上为准，先查版本差）
- 集成接口断点（工具各自正常，链路参数没接上）
- 验收记录缺口（行为正确只是没记录）

No cell is 功能缺失. Configurator bundle on both engines is the same file: `configurator.js?ver=e90a705b79f5bc1bc010`, 208659 bytes, sha256 `277692b3f931595049f493c636feca4006a6b7978448384532892ae14c839143`. It contains `openRoof` and does not contain `URLSearchParams`.

| Link | Pass | Fail | Class of the miss | Tickets |
| --- | ---: | ---: | --- | --- |
| size-hint prefill | 0 | 8 | 集成接口断点 | #457 |
| open_configurator landing | 4 | 4 | 验收记录缺口 | #458 |
| design → add all → Genie on the draft | 0 | 12 | 集成接口断点（数量）；加购与价格门通过 | #459 |
| `?step=roof`（#444 怀疑项，不在上表 28 格内） | 0 | 8 | 集成接口断点 | #462 |
| Total of the three links | 4 | 24 | | |

Price gate: held on every local draft cell. No amount on guest or pending. Approved draft shows net prices. No P0. Production price gate was not exercised (empty cart GET only).

## size-hint

Class: 集成接口断点.

Genie and `linker/size-hint` emit the stated fields. The configurator does not read them. Both engines agree, so this is not 行为损坏. `phase=3` on the form is the default, not a prefill. Guest and approved match on the local Genie turn. Units were not applied because the values were not written; no wrong-unit conversion was seen.

Production Genie turn was not run. The read-only equivalent is `GET linker/size-hint` with `input[lang]=de`, then opening that URL. Local and production both return the English path with `pv_kwp=10`, `annual_kwh=4500`, `phase=3`, `backup=needed`, `plz=80538`, and no `lang`. Opening it leaves plz, annual and kWp empty and backup `none` on both engines, 1440 and 390.

Precedent for a later fix: `SizeHint::execute` already builds those query keys (`plugins/linker-commerce/includes/Abilities/SizeHint.php`, fixture `services/genie/tests/fixtures/size-hint-urls.json`). `readConfig` only reads `element.dataset.step`. `Mount.php` does not copy the query onto the mount. Connect the existing keys to the existing form defaults. Do not invent a new field set.

| State | Lang | 1440 | 390 | Local | Production | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| guest | en | fail | fail | fields empty | same URL, fields empty | `shots/l1-guest-en-1440-configurator.png`, `shots/both-prod-prefill-1440.png` |
| guest | de | fail | fail | English path, fields empty | ability returns the English path; German page with the same fields also leaves kWp empty | `shots/l1-guest-de-1440-configurator.png`, `shots/both-prod-prefill-de-1440.png` |
| approved | en | fail | fail | fields empty | same as guest; no approved production session | `shots/l1-approved-en-1440-configurator.png` |
| approved | de | fail | fail | English path, fields empty | same as guest DE | `shots/l1-approved-de-1440-configurator.png` |

## open_configurator

English lands on the three-step rail (Inputs / Solution / Design report) and the app mounts, locally and on production (page GET).

German Genie turns open that same English page (`html lang=en-US`), not `/de/loesungskonfigurator/`. Class: 验收记录缺口. Not a broken page, and not a local/production split.

`#393` accepted `lang` on size-hint and then ignored it: it is not a configurator field, and the prefill still contains only fields the customer stated. The fixture locks the English path. Both engines' ability GET with `input[lang]=de` return that English path. A direct visit to `/de/loesungskonfigurator/` is German on both (`html lang=de-DE`, title Lösungskonfigurator, steps 01Eingaben / 02Lösung / 03Auslegungsbericht). Production Genie turn was not run; the ability result is the URL a German turn would be given.

A later change that emits `/de/loesungskonfigurator/` would contradict `#393` and the fixture. The record to keep is: a German sizing turn opens the English configurator URL, and the German page is the one at its own address.

| State | Lang | 1440 | 390 | Local | Production | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| guest | en | pass | pass | three-step rail | page GET, same rail | `shots/l2-guest-en-1440.png`, `shots/both-prod-prefill-1440.png` |
| guest | de | fail | fail | English path | ability URL is the English path; German page itself is German | `shots/l2-guest-de-1440.png`, `shots/both-prod-prefill-de-1440.png` |
| approved | en | pass | pass | three-step rail | page GET, same rail; no approved session | `shots/l2-approved-en-1440.png` |
| approved | de | fail | fail | English path | same ability URL as guest DE | `shots/l2-approved-de-1440.png` |

## Draft

Cell verdict is fail because Genie does not state the quantity. Class of that miss: 集成接口断点. Add-all and the price gate are not misses.

Passed, all six local state × language cells:

- Design status `solution` for PLZ 80538, 4500 kWh/year, 10 kWp, three-phase, backup `none` (spec 14).
- Add all. Confirmation: “All products are in your solution draft.” / “Alle Produkte sind in Ihrem Lösungsentwurf.”
- Draft lines: qty 1 of GW10K-ETA-G20 (3556) and qty 1 of GW6.0-BAT-D-G20 (3611).

Price gate held locally:

- Guest: “Log in for prices” / “Preise nach Anmeldung”. No amount.
- Pending: “Account under review. Prices after approval.” / “Ihr Konto wird geprüft. Preise nach Freigabe.” No amount.
- Approved: €1,090.00 and €1,430.00 (German format 1.090,00 € and 1.430,00 €).

Quantity: the draft page shows 1. Genie names the models and does not say 1. `PageContext::draft_ids()` passes English ids only. `page.py` `_draft()` stores `product_id` and `title` only. Spec 13 page perception for a draft is those ids via Store API `include`. The same cart already exposes quantity to handoff (`wc_load_cart()`: name, SKU, quantity). The seam is that the reader used for the answer does not receive the quantity the cart already has. Genie did not invent 1. That refusal matches the reader. It is not a missing design tool and not a missing draft.

Production: no turn and no add-to-draft. Read-only Store API `include=3556,3611` returns the same two products, EN and DE, on both engines. `/cart/` and `/de/loesungsentwurf/` return 200 with Genie mounted and nothing added. The quantity class is from the local chain plus the shared reader, not from a production turn.

Pending EN and approved EN screenshots show “Genie could not load this product.” That string is the card's unloaded state (`GenieCard` renders it while `product` is still null). Approved DE cards then showed the net prices. Not filed as its own defect. Production turn was not run. Logged-in DE panels also restored an earlier English thread; the new German cards are the language evidence, and that reuse is not a product bug.

| State | Lang | 1440 | 390 | Local | Production | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| guest | en | fail | fail | qty not stated; gate held | turn not run | `shots/l3-guest-en-1440.png` |
| guest | de | fail | fail | qty not stated; gate held | turn not run | `shots/l3-guest-de-1440.png` |
| pending | en | fail | fail | qty not stated; gate held | turn not run | `shots/l3-pending-en-1440.png` |
| pending | de | fail | fail | qty not stated; gate held | turn not run | `shots/l3-pending-de-1440.png` |
| approved | en | fail | fail | qty not stated; net prices on the draft | turn not run | `shots/l3-approved-en-1440.png` |
| approved | de | fail | fail | qty not stated; net prices on the draft and in the card DOM | turn not run | `shots/l3-approved-de-1440.png` |

Add-all shots: `shots/l3-<state>-<lang>-solution.png`.

A run that selected backup `needed` without a load and hours returned no candidate. The configurator stated that. That run is not a product failure and is not in `rows.json`.

## `?step=roof`

Class: 集成接口断点. Both engines. Not 行为损坏: the bundle hash matches, and the rendered mount has no `data-step` on either engine.

| Engine | URL | 1440 | 390 | `data-step` | `.linker-roof` | html lang |
| --- | --- | --- | --- | --- | --- | --- |
| local | `/solution-configurator/?step=roof` | closed | closed | absent | absent | en-US |
| local | `/de/loesungskonfigurator/?step=roof` | closed | closed | absent | absent | de-DE |
| production | `/solution-configurator/?step=roof` | closed | closed | absent | absent | en-US |
| production | `/de/loesungskonfigurator/?step=roof` | closed | closed | absent | absent | de-DE |

Redirects, one hop, both engines, query kept:

- `/design-canvas/` → `/solution-configurator/?step=roof`
- `/de/design-canvas/` → `/de/loesungskonfigurator/?step=roof`
- `/de/entwurfsflache/` → `/de/loesungskonfigurator/?step=roof`

After the hop the roof step is still closed. The redirect does its job.

The roof step itself opens on the established path. Local only (not clicked on production): postcode 80538, then “No PV figure yet? Estimate from the roof”. `.linker-roof` is visible and credits Bayerische Vermessungsverwaltung. Production shows the same button (“Noch keine PV-Leistung? Aus dem Dach abschätzen” on the German page) and serves the same bundle. Shot: `shots/both-local-roof-button-1440.png`.

A local HTML injection set `data-step="roof"` before the script ran. The canvas still did not open, and the postcode stayed empty. `ResidentialPanel` opens the step only when `config.openRoof && defaults.plz`. Nothing reads `plz` from the query, so a bare `?step=roof` has no postcode to pass. The button path, given an empty postcode, focuses that field instead of opening the map. Production was not injected.

Precedent for a later fix: connect the existing `step=roof` query to the existing `data-step` / `openRoof` path (`config.ts`, `Mount.php`). A query with no postcode should follow the button's empty-postcode behavior, not invent a map without a location. Spec 12's accepted check is that the retired URL lands on `?step=roof` in one hop. That check passes on both engines.

Shots: `shots/both-<local|prod>-step-roof-1440.png`, `shots/both-<local|prod>-step-roof-de-1440.png`, and the 390 pair. Record: `both-engines.json`.

## Production smoke

Read-only GET. Detail: `production-smoke.json`, `both-engines.json`.

| Check | Local | Production |
| --- | --- | --- |
| `linker/size-hint` with `input[lang]=de` | English URL, fields in the query, no `lang` | same |
| English configurator with those fields | mounted, kWp empty | mounted, kWp empty |
| German configurator with those fields | `de-DE`, kWp empty | `de-DE`, kWp empty |
| `?step=roof` EN and DE | query kept, roof closed | query kept, roof closed |
| Retired canvas URLs | 301 to `?step=roof`, roof closed | 301 to `?step=roof`, roof closed |
| `/cart/` and `/de/loesungsentwurf/` | used by the draft cells | 200, Genie mounted, nothing added |

## Local feed

Class: 行为损坏. Production is the authority. Version check first: both feeds are schema 1, compatibility `81f8688f5d0383bf275607b0aaaf4367963881f1b9c4c47f0450ac7b55f980e6`. Generated timestamps are 2026-10-20T17:34:25+00:00 (local) and 2026-10-20T17:34:31+00:00 (production). Not a tool-version split.

| Engine | Products | With figures | Document citation hosts |
| --- | --- | ---: | --- |
| local `GET /wp-json/linker/v1/engineering-feed` | 106 | 0 | `127.0.0.1:9231` (210) |
| production same route | 106 | 83 | `de-linker.com` (210) |

`EngineeringFeed::is_hosted_citation()` keeps only `de-linker.com` and `www.de-linker.com`. After pull load, local citations are the instance host, so every figure is dropped and a stock local engine cannot design. Production citations pass the same allowlist. This is not a configurator logic defect.

The draft cells above used the production feed file in the instance engine directory only. No product code was changed. Do not run `just serve m445` against that instance if the replacement must stay: serve rewrites the feed from the local endpoint.

## Defects

- #457 P1, 集成接口断点: configurator ignores size-hint query fields. Both engines. Precedent: size-hint query keys vs `readConfig` / `Mount.php`.
- #458 P1 retitled, 验收记录缺口: German sizing opens the English configurator URL. That matches `#393` and the fixture. German page works at its own URL. No code change unless a new ruling overrides `#393`.
- #459 P1, 集成接口断点: draft answer has no quantity. Cart quantity and the handoff reader already have it; `draft_ids()` / `_draft()` pass id and title only. Production turn not run.
- #460 P1, 行为损坏: local engineering feed drops every figure after pull load. Production feed is the authority. Same compatibility hash.
- #462 P1, 集成接口断点: `?step=roof` does not open the roof step on either engine. Roof step opens from the postcode button. Redirects already preserve the query.

No price leak. No mail sent. No product code changed.
