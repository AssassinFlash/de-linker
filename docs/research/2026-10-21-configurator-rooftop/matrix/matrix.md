# Genie ↔ Configurator matrix (#445)

Local instance `m445` (`http://127.0.0.1:9231`, engine `9232`, Genie `9233`), snapshot `20261019-1715` (taken 2026-10-19T09:18:02+00:00). Production calls are GET only: no turn, no add-to-draft, no account, no mail.

| Link | Pass | Fail | Tickets |
| --- | ---: | ---: | --- |
| size-hint prefill | 0 | 8 | #457, #458 |
| open_configurator landing | 4 | 4 | #458 |
| design → add all → Genie on the draft | 0 | 12 | #459 |
| Total | 4 | 24 | |

Price gate: held on every draft cell. No amount on guest or pending. Approved draft shows net prices. No P0.

## size-hint

Genie emits the stated fields. The configurator does not read them. `phase=3` on the form is the default, not a prefill. Guest and approved match. Units were not applied because the values were not written; no wrong-unit conversion was seen.

German answers use the English path. See #458.

| State | Lang | 1440 | 390 | Evidence |
| --- | --- | --- | --- | --- |
| guest | en | fail | fail | `shots/l1-guest-en-1440-configurator.png`, `shots/l1-guest-en-390-configurator.png` |
| guest | de | fail | fail | `shots/l1-guest-de-1440-configurator.png`, `shots/l1-guest-de-390-configurator.png` |
| approved | en | fail | fail | `shots/l1-approved-en-1440-configurator.png`, `shots/l1-approved-en-390-configurator.png` |
| approved | de | fail | fail | `shots/l1-approved-de-1440-configurator.png`, `shots/l1-approved-de-390-configurator.png` |

Observed URL, both languages: `/solution-configurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538`. Form after open: plz, annual and kWp empty; backup `none`.

## open_configurator

English lands on the three-step rail (Inputs / Solution / Design report) and the app mounts. German lands on that same English page (`html lang=en-US`), not `/de/loesungskonfigurator/`.

| State | Lang | 1440 | 390 | Evidence |
| --- | --- | --- | --- | --- |
| guest | en | pass | pass | `shots/l2-guest-en-1440.png`, `shots/l2-guest-en-390.png` |
| guest | de | fail | fail | `shots/l2-guest-de-1440.png`, `shots/l2-guest-de-390.png` |
| approved | en | pass | pass | `shots/l2-approved-en-1440.png`, `shots/l2-approved-en-390.png` |
| approved | de | fail | fail | `shots/l2-approved-de-1440.png`, `shots/l2-approved-de-390.png` |

A direct visit to `/de/loesungskonfigurator/` is German. The miss is the deep link, not a missing page. Production: `shots/prod-cfg-de-1440.png` (`html lang=de-DE`, title Lösungskonfigurator, kWp still empty).

## Draft

Cell verdict is fail because Genie does not state the quantity. The other two parts of this link passed.

Passed, all six state × language cells:

- Design status `solution` for PLZ 80538, 4500 kWh/year, 10 kWp, three-phase, backup `none` (spec 14).
- Add all. Confirmation: “All products are in your solution draft.” / “Alle Produkte sind in Ihrem Lösungsentwurf.”
- Draft lines: qty 1 of GW10K-ETA-G20 (3556) and qty 1 of GW6.0-BAT-D-G20 (3611).

Price gate held:

- Guest: “Log in for prices” / “Preise nach Anmeldung”. No amount.
- Pending: “Account under review. Prices after approval.” / “Ihr Konto wird geprüft. Preise nach Freigabe.” No amount.
- Approved: €1,090.00 and €1,430.00 (German format 1.090,00 € and 1.430,00 €).

Failed: Genie names the models and says the page does not print a quantity. The draft page quantity fields show 1. `PageContext::draft_ids()` passes ids only; `page.py` `_draft()` stores id and title only. Pending EN and approved EN also show “Genie could not load this product.” Approved EN does not show the net price in the visible answer. #459.

| State | Lang | 1440 | 390 | Evidence |
| --- | --- | --- | --- | --- |
| guest | en | fail | fail | `shots/l3-guest-en-1440.png`, `shots/l3-guest-en-390.png` |
| guest | de | fail | fail | `shots/l3-guest-de-1440.png`, `shots/l3-guest-de-390.png` |
| pending | en | fail | fail | `shots/l3-pending-en-1440.png`, `shots/l3-pending-en-390.png` |
| pending | de | fail | fail | `shots/l3-pending-de-1440.png`, `shots/l3-pending-de-390.png` |
| approved | en | fail | fail | `shots/l3-approved-en-1440.png`, `shots/l3-approved-en-390.png` |
| approved | de | fail | fail | `shots/l3-approved-de-1440.png`, `shots/l3-approved-de-390.png` |

Add-all shots: `shots/l3-<state>-<lang>-solution.png`.

A run that selected backup `needed` without a load and hours returned no candidate. The configurator stated that. That run is not a product failure and is not in `rows.json`.

## Production smoke

Read-only GET.

| Check | Result |
| --- | --- |
| `linker/size-hint` with `input[lang]=de` | English URL, fields in the query, no `lang` |
| English configurator with those fields | 200, mounted, kWp empty |
| `/de/loesungskonfigurator/` with the same fields | 200, `de-DE`, kWp empty |
| `/cart/` and `/de/loesungsentwurf/` | 200, Genie mounted, nothing added |

Record: `production-smoke.json`. Shots: `shots/prod-size-hint-url-1440.png`, `shots/prod-size-hint-url-390.png`, `shots/prod-cfg-de-1440.png`, `shots/prod-cfg-de-390.png`, `shots/prod-cart-en-1440.png`, `shots/prod-cart-en-390.png`, `shots/prod-cart-de-1440.png`, `shots/prod-cart-de-390.png`.

## Local feed

After pull load, `GET /wp-json/linker/v1/engineering-feed` has 106 products and 0 figures. Document hosts are `127.0.0.1:9231` (210). `EngineeringFeed::is_hosted_citation()` keeps only `de-linker.com` and `www.de-linker.com`, so every citation is dropped and a stock engine cannot design. #460.

The draft cells above used the production feed file in the instance engine directory only. No product code was changed. Do not run `just serve m445` against that instance if the replacement must stay: serve rewrites the feed from the local endpoint.

## Defects

- #457 P1: configurator ignores size-hint query fields.
- #458 P1: size-hint URL ignores language; German open_configurator opens the English page.
- #459 P1: Genie draft context has no quantities.
- #460 P1: local engineering feed drops every figure after pull load.

No price leak. No mail sent.
