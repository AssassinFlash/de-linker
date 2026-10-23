# Homepage inquiry guidance

The final homepage scene currently offers online ordering, although the current
business contract is inquiry → team-prepared quote/Proforma → offline follow-up.
Repair only its H4 and first paragraph in English and German. Preserve every
other content byte, all three authorized customer quotes, images, scripts,
styles, CTA labels, destinations and data attributes. Guest inquiries stay open;
account approval and sign-in gate net prices, with inquiry-only products retained.

English source, followed by independently phrased German from the same facts:

| Language | Heading | First paragraph |
| --- | --- | --- |
| EN | Net prices and project quotes. | Approved partners can view net prices when signed in. Our team prepares equipment quotes in response to your inquiry, whether or not you have an account. |
| DE | Nettopreise und Projektangebote. | Mit einem freigeschalteten Konto sehen Sie Nettopreise, wenn Sie angemeldet sind. Unser Team erstellt Angebote für die benötigten Geräte auf Anfrage, auch ohne Kundenkonto. |

Copy record: draft `24bfc0fd0f6149b2c081a8ec6c62b87237b40de31d2b4552a40fffba4807c4b5`
→ independent review `e04d3ba40537fdf8b2f4802b4f815400e18beed786a065604fcb104197e9c366`
→ accepted minimal changes in `home-scene-inquiry-copy-final.json` under the
existing `home-image-loading-20261023T0130Z` evidence directory. The review applied
linker-copywriting and embedded humanizer, with current project rules overriding
obsolete online-ordering examples. Owner confirmed all three quotes real and
authorized; none is rewritten.

## Native mechanisms and save boundary

This is saved LC page content; no runtime plugin layout, CSS, model route or new
UI is introduced. LC editing updates one document; it does not atomically save
both reviewed language documents and their existing translation baseline.
WooCommerce has no role in this content save. Reuse the hardened content writer
unchanged and native `Translator::adopt_current`; do not build another translator.

`home-inquiry-copy.py` recognizes exactly one known LC scene prefix per language
and replaces only the two text nodes. Unknown, duplicate and partially updated
pairs fail closed. Repeating the complete final pair makes no write and also
requires its native translation baseline to be current.

`reviewed-page-pair.php` wraps the existing writer in CLI only. It verifies the
explicit native EN/DE pair and InnoDB postmeta. The existing writer locks both
post rows, validates backed-up content and preserves backslashes with `wp_slash`.
A first `pre_post_update` hook locks the pair's metadata before native baseline
priming and compares the four saved translation keys with the backup. The final
German `post_updated` hook adopts the reviewed baseline before COMMIT; native
`wp_update_post(..., true, false)` skips translation-queue after-insert hooks.
The installed WordPress source fires `post_updated` before returning even with
that flag false. A final COMMIT guard verifies adoption. A rejecting Client is
used; reviewed copy must never call a model. Hooks are removed in `finally`.

The baseline delta is limited to EN status/note and DE source hash/segment units.
Rollback checks the installed pair and baseline against the saved successful
result, then atomically restores original content and the exact four **value
lists**. Native metadata IDs can change during successful rollback; historical
review records and all other metadata are preserved. A thrown transaction rolls
back the original rows themselves. A lost COMMIT acknowledgment remains unknown:
independently read both contents and the baseline before retrying or reversing.

## Candidate checks and limits

The application CLI is restricted to owned local `http://127.0.0.1:9410`, IDs
13/6913. Production is read-only during the parallel production writer's window.
Before local application, verify the retained recovery SQL and save a fresh exact
content/baseline record; do not create another full instance or per-round SQL.
Fresh independent readback must match both planned contents and native baseline.

Required isolated native fixtures: normal paired adoption and successful rollback;
source drift; metadata drift; second-page write failure; and failure after
adoption but before COMMIT. Every failure must preserve both original contents
and all four original metadata value lists. Fixtures create/delete only their
own private language pair; no mail, model or inquiry submission is permitted.

Browser checks after application: EN/DE × 1440/390/320, actual platform fonts,
contained text and CTA geometry, hover/focus, actual CTA navigation to the same
localized offer-intent contact consumer, no real submission. Recheck homepage
scripts/quotes and privacy content, backslashes, translation queue and business
counters independently. Source review, runtime fixtures, visual approval, CI and
production readback are separate gates; source or copy PASS does not close them.

Database maintenance currently prevents native fixtures and page application.
No candidate content has been installed or deployed at this specification stage.
