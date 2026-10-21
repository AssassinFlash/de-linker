# #473 the German save link opens the German account page

2026-10-21. Local snapshot instance only. No merge, no deploy, no production write, no mail, no inquiry, no registration.

Instance: `fix473` (`just up fix473`, `just pull load fix473 latest`, `just serve fix473`) at `http://127.0.0.1:9249`, snapshot `20261019-1715`. Build walked: `configurator.js?ver=bacae88a042528100047`, sha256 `7ac9d249d7afd305f1ec0d63c7f1475aecc8d9f3efb48a29072c8ec5af5eaee5`, 209422 bytes.

Harness: `walk.mjs` (guest and member; clicks, does not inject). Record: `record.json`.

## The miss

`SavedSolutions::url()` (`plugins/linker-commerce/includes/Account/SavedSolutions.php:168-171`) calls `wc_get_account_endpoint_url( 'saved-solutions' )`. That function is language-blind in itself; what makes it German is the request's language: linker-i18n's `RestLang` enters the `?lang=` language for a REST callback, `Storefront::page_id` then answers the German my-account page id, and `GermanRoutes::link` (on `woocommerce_get_endpoint_url`) rewrites `saved-solutions` to `gespeicherte-loesungen` because the path now starts `/de/`.

The configurator's save never sent `lang`, so the route ran in English and answered `/my-account/saved-solutions/`. The page being German changed nothing.

Probe before the change (pre-fix instance `c351`, direct POST, guest):

| Request | Answered `url` |
| --- | --- |
| `POST /wp-json/linker/v1/solutions` | `http://127.0.0.1:9153/my-account/saved-solutions/` |
| `POST /wp-json/linker/v1/solutions?lang=de` | `http://127.0.0.1:9153/de/mein-konto/gespeicherte-loesungen/` |

That is the whole defect: the client had to name the page's language.

## The change

`solutions.ts` sends `?lang=` (`saveSolution` takes the page's `locale`), the same way `store.ts` asks for products (#413's Storefront link precedent, and #393's size-hint `lang` precedent). `ResidentialPanel.save` passes `config.locale`; the Genie card save (`cardActions.ts`) passes its `locale`. No PHP changed: the language-aware link already exists and now receives the language.

Product reads, page renders and every other link are unchanged.

## Guest, both languages

Fixture: PLZ 80538, 4500 kWh/year, 10 kWp, three-phase, backup not needed. Save clicked after Add all. Guest = no login (202, `id: 0`).

| | Before (#472, local `127.0.0.1:9153`) | After (fix473) |
| --- | --- | --- |
| EN POST | `/my-account/saved-solutions/` | `/my-account/saved-solutions/` (unchanged) |
| EN opened | `lang=en-US`, “Partner Account: Sign In or Register” | `lang=en-US`, “Sign in” wall |
| DE POST | `/my-account/saved-solutions/` | `/de/mein-konto/gespeicherte-loesungen/` |
| DE opened | `lang=en-US`, English sign-in wall | `lang=de-DE`, “Anmelden”, “Ihr Partner-Konto” |

The opened "Open saved solution" / "Gespeicherte Lösung öffnen" link is the answered `url` (`record.json`, `saved.saveHref` = `accountRequested` in both languages).

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Guest saved | [en-guest-save-1440](shots/en-guest-save-1440.png) | [en-guest-save-390](shots/en-guest-save-390.png) | [de-guest-save-1440](shots/de-guest-save-1440.png) | [de-guest-save-390](shots/de-guest-save-390.png) |
| Guest wall | [en-guest-account-1440](shots/en-guest-account-1440.png) | [en-guest-account-390](shots/en-guest-account-390.png) | [de-guest-account-1440](shots/de-guest-account-1440.png) | [de-guest-account-390](shots/de-guest-account-390.png) |

## Member, both languages

One logged-in context (a one-time local login link, no mail; `wp user create`, no mail). Save is 201 with the solution's fragment.

| | Returned and opened |
| --- | --- |
| EN | `…/my-account/saved-solutions/#linker-solution-7442`, `lang=en-US`, list “Saved solutions” |
| DE | `…/de/mein-konto/gespeicherte-loesungen/#linker-solution-7443`, `lang=de-DE`, list “Gespeicherte Lösungen” |

The German list shows both saves (“Gespeichert am 21. Oktober 2026”), each with its products and “Auslegungsbericht (PDF)”. The English list shows the same two.

| State | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Member saved | [en-member-save-1440](shots/en-member-save-1440.png) | [en-member-save-390](shots/en-member-save-390.png) | [de-member-save-1440](shots/de-member-save-1440.png) | [de-member-save-390](shots/de-member-save-390.png) |
| Member list | [en-member-account-1440](shots/en-member-account-1440.png) | [en-member-account-390](shots/en-member-account-390.png) | [de-member-account-1440](shots/de-member-account-1440.png) | [de-member-account-390](shots/de-member-account-390.png) |

`record.json` `memberUser: 401` is the REST `/wp/v2/users/me` check without a REST nonce, which answers 401 to a cookie session; the 201 saves are the login proof.

## Tests

- JS: `solutions.test.ts` asserts the POST address `…/linker/v1/solutions?lang=en` and `?lang=de` and the answered URL per language; `cardActions.test.tsx` asserts the card's save carries the page language both ways; `App.test.tsx` asserts the German configurator and the English one pass their locale.
- PHP: `SavedSolutionsTest::test_the_open_link_follows_the_request_language` (integration, snapshot instance): guest `lang=en` → English account URL, guest `lang=de` → German account URL, logged-in German save → German URL with the fragment. Runs with `LINKER_WP_ROOT=… plugins/linker-commerce/vendor/bin/phpunit -c phpunit.integration.xml.dist --filter SavedSolutionsTest`.

## After deploy

Production re-verification is due once this lands: repeat the guest save on `de-linker.com` in both languages and open the answered link (expect `https://de-linker.com/de/mein-konto/gespeicherte-loesungen/` in German). Not done here: no deploy.

## Cleanup

Guest drafts emptied (`remove-item` 200 ×2 each language, cart read 0). The member's two saved solutions (7442, 7443) and the test customer were deleted after the walk; no inquiry, no registration, no mail.
