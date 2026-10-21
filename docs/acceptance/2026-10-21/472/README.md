# #472 add-all and save on production

2026-10-21. Guest walk only. No product-code change. No inquiry, no registration, no login, no mail.

Production writes were the walk's own draft writes: Store API `cart/add-item` from the Add all button, `POST linker/v1/solutions`, then `cart/remove-item`. Each language ended with a cart read of remaining 0. Cookie values and cart item keys are not in this record.

Harness: `walk.mjs` (clicks the button; does not inject lines). Local URL check: `local-save.mjs` against `http://127.0.0.1:9153`. Reference cleanup is the #445 probe (`docs/research/2026-10-21-configurator-rooftop/matrix/production-draft.mjs`).

## What was walked

Fixture from spec 14 / the #445 probe: PLZ 80538, 4500 kWh/year, 10 kWp, three-phase, backup not needed.

Production bundle `configurator.js?ver=5ea89b36c5f6f438824b`, sha256 `26719fe1ae045d434ad4acfc8d8913f100c52de5474d1a777262ea07fd64351a`, 209080 bytes. Walk `2026-10-20T23:49:12Z`. Both languages: `users/me` 401, no `wordpress_logged_in` cookie.

Design status `solution`. Product lines 3556 GW10K-ETA-G20 ×1 and 3611 GW6.0-BAT-D-G20 ×1. Five installer lines have no product id.

POSTs: `design/residential`, `cart/add-item` ×2, `linker/v1/solutions`, `cart/remove-item` ×2, plus Google Analytics `collect` after the consent banner was accepted so the page could be shot. `forbiddenPosts` is empty. Download PDF was not clicked (#470 / C39). Send inquiry was not clicked.

## Pass / fail

| Link | EN | DE | Class | Result |
| --- | --- | --- | --- | --- |
| Three screens | Pass | Pass | 验收记录缺口, now recorded | Pass |
| Design report sections | Pass | Pass | 验收记录缺口, now recorded | Pass |
| Add all, lines and quantities | Pass | Pass | 验收记录缺口 (C27, not re-walked after cutover), now recorded | Pass |
| Guest price gate on the draft page | Pass | Pass | 验收记录缺口, now recorded | Pass |
| Guest save button | Pass | Pass | C30 button path was 实现未验; the 202 path is now recorded | Pass |
| German open-link language | English URL is the English page | Fail | 集成接口断点 | Fail. #473 |
| Account list and `claim()` | Login wall, not entered | Login wall, not entered | 本地已验·线上待测 | Not a new defect |

C09 (step rail `current` stuck on 01) is already 规格错配. This walk did not re-file it. C39 was not clicked.

## Three screens

One page, three sections. EN `html lang=en-US`, rail Inputs / Solution / Design report. DE `html lang=de-DE`, rail Eingaben / Lösung / Auslegungsbericht.

Report section ids, both languages: `linker-report-site`, `linker-report-yield`, `linker-report-storage`, `linker-report-metrics`, `linker-report-basis`, `linker-report-releases`, `linker-report-bom`, `linker-report-assumptions`, `linker-report-next`. EN titles include Bill of materials. DE titles include Stückliste. No `€` or `EUR` amount in the report text. No warnings block on this design.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Inputs | [en-inputs-1440](shots/en-inputs-1440.png) | [en-inputs-390](shots/en-inputs-390.png) | [de-inputs-1440](shots/de-inputs-1440.png) | [de-inputs-390](shots/de-inputs-390.png) |
| Solution | [en-solution-1440](shots/en-solution-1440.png) | [en-solution-390](shots/en-solution-390.png) | [de-solution-1440](shots/de-solution-1440.png) | [de-solution-390](shots/de-solution-390.png) |
| Design report | [en-report-1440](shots/en-report-1440.png) | [en-report-390](shots/en-report-390.png) | [de-report-1440](shots/de-report-1440.png) | [de-report-390](shots/de-report-390.png) |

## Add all

Button clicked: “Add all to solution draft” / “Alles zum Lösungsentwurf hinzufügen”. Confirmation exact: “All products are in your solution draft.” / “Alle Produkte sind in Ihrem Lösungsentwurf.”

Cart read-back after the click, both languages: 3556 ×1, 3611 ×1. `lineDiff` empty. The five installer lines were not added. Draft page DOM: those two products, quantity 1. Cart badge 2.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Added | [en-added-1440](shots/en-added-1440.png) | [en-added-390](shots/en-added-390.png) | [de-added-1440](shots/de-added-1440.png) | [de-added-390](shots/de-added-390.png) |
| Draft | [en-draft-1440](shots/en-draft-1440.png) | [en-draft-390](shots/en-draft-390.png) | [de-draft-1440](shots/de-draft-1440.png) | [de-draft-390](shots/de-draft-390.png) |

## Price gate

Visible draft, both languages: no `.woocommerce-Price-amount`. EN “Log in for prices”. DE “Preise nach Anmeldung”. Note present: inquiry without an account, net prices after approval. No `€` or `EUR` in the draft text.

Store API cart, production only, both lines: `prices` is an object, not null. `price`, `regular_price`, `raw_prices.price`, `line_total`, and `totals.total_price` are `"0"`. That is not a net amount. `StoreApiPrices` nulls `/wc/store/v1/products` only (`plugins/linker-commerce/includes/Gating/StoreApiPrices.php`). The draft page does not render these zeros. Not filed. Local cart route was not walked, so this is not called a functional defect.

## Guest save

Button “Save solution” / “Lösung speichern”. Both languages: HTTP 202, body `{id: 0, url: https://de-linker.com/my-account/saved-solutions/}`. UI: “Saved to your account. Open saved solution” / “In Ihrem Konto gespeichert. Gespeicherte Lösung öffnen”.

That matches `SolutionsRoute`: a guest is kept in the WooCommerce session and gets 202 with id 0. No account post. `document.cookie` gained no claim-cookie name; the session cookie is HttpOnly and is not in this record. C30's “claim cookie” wording is the file comment. The route that answered is the session keep.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Saved | [en-save-1440](shots/en-save-1440.png) | [en-save-390](shots/en-save-390.png) | [de-save-1440](shots/de-save-1440.png) | [de-save-390](shots/de-save-390.png) |

## German open link — fail, #473

The German page is German. The open link is not.

Both engines, guest POST from the German configurator, returned the English account URL. Opening it stays on that URL: `html lang=en-US`, title “Partner Account: Sign In or Register”, password field present, nothing submitted.

| Engine | Page lang | Returned URL | Opened |
| --- | --- | --- | --- |
| Production | `de-DE` | `https://de-linker.com/my-account/saved-solutions/` | `en-US` login wall |
| Local `127.0.0.1:9153` | `de-DE` | `http://127.0.0.1:9153/my-account/saved-solutions/` | `en-US` login wall |

Local bundle is older (`ver=e90a705b79f5bc1bc010`). The URL is built in PHP `SavedSolutions::url()`, so the bundle gap does not explain it. Same miss on both engines: not 行为损坏.

Direct GET `https://de-linker.com/de/mein-konto/gespeicherte-loesungen/` is 200, `lang=de-DE`, title “Gespeicherte Lösungen | Linker”. `/de/mein-konto/saved-solutions/` 301s there. The German account page works. The save response does not point at it.

Class: **集成接口断点**. `solutions.ts` does not send `?lang=` (product reads in `store.ts` do). `RestLang` therefore stays on English for this POST. `wc_get_account_endpoint_url( 'saved-solutions' )` emits `/my-account/saved-solutions/`. `GermanRoutes` only rewrites `saved-solutions` to `gespeicherte-loesungen` when the path already starts with `/de/`. Precedent is that existing German account URL, not a new slug. #393 does not cover this link. Filed as #473. Not fixed here.

Logged-in save uses the same `url()` and was not walked.

Shots: [de-account-1440](shots/de-account-1440.png), [de-account-390](shots/de-account-390.png). English open link, for comparison, is the English login wall: [en-account-1440](shots/en-account-1440.png), [en-account-390](shots/en-account-390.png).

## Account list — 本地已验·线上待测

The list behind the open link needs a customer login. This walk did not log in and did not register. Registration sends mail. Test mail discipline: no mail. The open link was followed as a GET and stopped on the login wall. `claim()` was not exercised.

Logged-in save was already recorded locally on 2026-10-10 (inventory C29, `docs/acceptance/2026-10-10/14/solution-*-saved.png`). That is the local verification. Production login was not opened, so the account list stays 本地已验·线上待测. `claim()` itself was 实现未验 (C30) and is still unwalked. That is not reclassified as a defect: this walk did not measure a failed claim.

## Production cleanup

Both languages, after the draft shots:

- `remove-item` 200 for 3556 and 3611
- `emptied.remaining` 0, `left` []
- follow-up cart GET `items` []

Page after that read: “Your solution draft is empty.” / “Ihr Lösungsentwurf ist leer.” Cart icon has no count.

[en-emptied-1440](shots/en-emptied-1440.png), [de-emptied-1440](shots/de-emptied-1440.png). Emptied was shot at 1440 only. The 390 cleanup is the same cart read, not a second screenshot.

Guest save id is 0, so no account post was created. The browser context was closed, which drops the session cookie, so `claim()` cannot run for this walk. No public delete of the anonymous session key was attempted. No second production write after the read-back of 0.

Local save sessions were the same shape (202, id 0) and were discarded when that context closed. They were not production.
