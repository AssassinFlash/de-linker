# Theme leak fix: the old project's head code, off the rebuilt site

Found 2026-10-13 while running the zero-legacy gate on t110 after the four
lanes landed. The gate's own TerraVolt-word warning had pointed at
`/products/`; tracing it found the emitter is not a template and not a plugin
row in any table the earlier sweep looked at, but **the active child theme's
`functions.php`** on the snapshot — about 570 lines of the old project's code
executing on every page.

A second headline leak surfaced while re-running the e2e suite: the **parent
theme picostrap5's own `inc/clean-head.php`** replaces every sign-in error
through the `login_errors` filter (WooCommerce applies that filter to the
my-account form's notices, `class-wc-form-handler.php:1265`) with the old
project's snark line — so the approval gate's refusal ("This account is not
approved for sign-in. We have emailed you the reason. …", ticket 73) never
reached the customer. Both leaks live in theme files the snapshot brought and
the cutover did not deploy.

## What it was doing on t110 (before)

`gate-before.txt` — the hardened gate, run before the fix: 11 problems.

- **A second, conflicting hreflang set.** The old emitter printed
  `hreflang="de"` → `https://tvolt-energie.de/...` on `/`, `/contact/`,
  `/products/`'s neighbours in its map, blog posts, product pages — on top of
  Polylang's correct set (`de` → `https://de-linker.com/de/...`). Google got
  two contradictory German alternates, one of them on the retired domain.
- **Old-brand archive JSON-LD.** `tv-archive-collection-jsonld` with
  `"name":"TerraVolt Product Families"`, `"isPartOf":{"name":"TerraVolt
  Energie GmbH"}` on `/products/` and `/de/produkte/`.
- **A contact-page script comment** naming `terravolt-b2b-core
  contact-request.js` (inside the pulled live page's own script, post 28).
- Inert leftovers: CDN enqueues (lottie/taos/alpine/preline) nothing in this
  repository or its content uses, and a bootstrap child copy that no page
  loads. Also in the file: the security headers and the REST user guard —
  both worth keeping.

## What changed (this repository owns each layer now)

| Layer | File | What it is |
|---|---|---|
| Theme file | `themes/picostrap5-child-base/functions.php` | The child theme's whole file, replacing the theme's at deploy: two behaviours (the `js` class, Picostrap's light marker). Everything else moved to its owner below. |
| Site hardening | `mu-plugins/linker-site-guards.php` | The four security headers and the REST user-enumeration guard, as a must-use plugin (ships via the existing mu-plugins deploy). |
| Structured data | `plugins/linker-commerce/includes/Storefront/ArchiveSchema.php` | The archive's CollectionPage + BreadcrumbList, built from the page's own sources (shop link/word from WooCommerce and the translations, the term from its own object, the same `breadcrumb`-context "Home" label the visible crumb uses). Unit-tested. |
| hreflang | — | Nothing to write: Polylang's set is correct on the rebuilt site (verified below); the competing emitter is gone with the theme file. |
| Sign-in message | `plugins/linker-commerce/includes/Registration/Approval.php` | The gate owns what a failed sign-in reads (priority 20, so the theme's blanket line loses): the approval refusal passes through whole, every credential error reads one generic line — a missing username and a wrong password look the same. Unit-tested; DE translation added and `msgid`-compiled. |
| Content | `tools/migrate/68-contact-form.py` | Third edit added: the page script's comment loses the old runtime's name; a page naming the old tree anywhere else is refused, and `verify` fails if the word survives. |
| Local stack | `tools/local/src/linker_local/{checkout,wordpress}.py` | `just up` now installs the repo's mu-plugins and its theme files over the instance (after the snapshot, so the checkout wins). |
| Cutover | `tools/cutover/src/linker_cutover/{plan,steps,cli}.py` | Step 3 deploys `themes/<slug>/<file>` over `wp-content/themes/<slug>/<file>` (replaced/created reported); a checkout without `themes/` stops the step, like the must-use directory. |
| Gate | `tools/checks/legacy-surfaces.py` | TerraVolt words and `tvolt-energie.de` are failures now, not warnings; the sweep adds the contact pages and a product page (Store API discovery). |

Also fixed on the way: `just e2e <name>` passed the instance name into
playwright's file filter (`positional-arguments` leaves it in `$1`), so the
recipe as documented in `tests/e2e/README.md` could not run; and
`68-contact-form.py`'s `--base` default pointed at the script's old t68
instance — the reference instance (t110) is the default now.

## Evidence after the fix

- `gate-after.txt` — the same hardened gate: **CLEAN**, every page `0 asset
  reference(s), 0 TerraVolt word(s), 0 old-domain reference(s)`.
- `head-after.txt` — one hreflang set per page (Polylang's, `/de/` paths,
  x-default → EN); the archive blocks now read `"name":"Products"` /
  `"name":"Produkte"`, `"isPartOf":{"name":"Linker"}`; the four security
  headers answer; `<html lang="en-US" data-theme="light">` and the `js` class
  still arrive; `68 verify` passes on both contact pages.
- Sign-in messages, probed on t110 after the fix: a rejected account reads the
  refusal with the reason and the way back (EN and DE, the German from the
  compiled catalog); a wrong password and an unknown username read the same
  one line.
- Unit tests: `ArchiveSchemaTest` + `ProductSchemaTest` 21/21; `ApprovalTest`
  16/16 (8 integration cases skip without WordPress, as before); cutover
  56/56; migrate `test_68_contact_form.py` 5/5; phpcs + phpstan clean on every
  touched project.
- E2E (`just e2e t110`, 73 tests): `e2e-after.txt` — see the note below on
  the four stale predicates the merged account lane had left in the suite.

## Known, pre-existing, not this fix's scope

- SEOPress still emits its own Product node on product pages (brand
  "Linker", category "Energy storage system", no sku) beside ours — a stored
  schema template row, documented in `ProductSchema`'s docblock before this
  change. Our node carries the product's real facts; the duplicate is a
  separate item.
- The posted-comparison note: the LIVE site's current theme file emits the
  same shape with Linker wording and single-domain hreflang — the cutover
  replaces that file with ours, so live's emitter leaves with it.
- The German catalog has 80 untranslated entries in `linker-commerce` alone
  (`msgattrib --untranslated --no-obsolete`, the authoritative count; a PO
  entry whose `msgstr ""` continues on following lines is translated and is
  not counted). Entries that read English to a German customer are their own
  round: they need a coverage check, not a sweep in passing.
- The e2e suite carried four stale predicates from before the account lane
  merged: `signIn` required exactly one `customer-logout` link, while the
  merged design renders the header menu's and the workplace sidebar's.
  Updated to "at least one" (two places), the two `toHaveCount(1)` asserts
  likewise, and `commerce.spec.ts`'s `toBeVisible()` now names `.first()`
  (strict mode saw two).
