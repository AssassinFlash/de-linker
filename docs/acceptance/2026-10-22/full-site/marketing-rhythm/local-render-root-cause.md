# Local saved-page rendering: read-only root-cause investigation

Verdict: the Service and Utility failures on local instance `sharedarchives` (9290) come from stale saved page content. Production already contains the narrowly repaired inline blocks. The local and production LiveCanvas enable meta and selected native page templates agree. Adding LiveCanvas meta or removing WordPress formatting globally would introduce a new behavior difference.

This investigation performed only local native CLI reads, in-process formatting/sanitization probes, pure Python transformations, `node --check`, and narrowly scoped SSH reads of public page content and the two relevant installed source hashes. It did not use a browser, save a post, change an option/meta value, run a model, submit a form, import a database, or deploy. Files written by the reviewer are this report, its public inventory, and private diagnostic evidence. Parent-owned browser records and production HTTP syntax results are identified separately below.

## Native causal chain

The installed Picostrap `page-templates/empty.php:16–18` calls `the_content()`; selecting this template does not bypass the content filters. Installed LiveCanvas `livecanvas-plugin-index.php:228–234` considers a page to use LC only when `_lc_livecanvas_enabled == '1'` (or it is an LC content type). Its `modules/content-filtering.php:9–14` returns immediately for a non-LC page; removal of `wptexturize` and `wpautop` occurs only in the LC branch at lines 33–37. Picostrap's fallback `inc/content-filtering.php:18–19` also exits when LC is installed. LC's `disable-ob-handling` option is used only by its editor raw-content helper at lines 64–81, not by this normal-page branch.

Service 2748/6700 and Utility 1755/6917 have no `_lc_livecanvas_enabled` meta and use `page-templates/empty.php` on **both** systems. The local native probe leaves `wpautop` at priority 10. Residential 749 is the positive control: native LC is true and the same native LC handler removes `wpautop` before its full content-filter chain. No LC enable-setting change is indicated.

The critical installed sources also match production exactly:

| Source | Local and production SHA-256 |
| --- | --- |
| LiveCanvas `modules/content-filtering.php` | `96d614738ef45c7e9ef925bc73daa7ed2202fa14546fdf55c29c6c57df03c351` |
| WordPress `wp-includes/formatting.php` | `350f6b32303915df970bb0e3ea360fcd54bb0b8a7ecc3d504c3d860ab9468d32` |

WordPress `wpautop()` first splits double newlines into paragraphs, then protects script/style newlines only during its later line-break phase (`formatting.php`, approximately lines 534–585). Thus the fact that raw `post_content` contains no paragraph tag does not prove that `the_content()` will leave its script intact.

The decisive comparison uses actual saved local content, the installed native formatter, and the full installed `the_content` callback chain. Each page runs in its own CLI process:

| Page | Raw scripts failing syntax | `wptexturize` only | `wpautop` only | Full local chain | Production raw through the same local chain |
| --- | ---: | ---: | ---: | ---: | ---: |
| Service EN 2748 | 0/5 | 0/5 | 4/5 | 4/5 | 0/5 |
| Service DE 6700 | 0/5 | 0/5 | 4/5 | 4/5 | 0/5 |
| Utility EN 1755 | 0/3 | 1/3 | 2/3 | 2/3 | 0/3 |
| Utility DE 6917 | 0/3 | 1/3 | 2/3 | 2/3 | 0/3 |
| Residential EN 749, LC control | 0/4 | 0/4 | 3/4 when forced directly | 0/4 after native LC setup | 0/4 |

For Service, the four script SHAs produced by `wpautop(raw)` match the full native chain and the previously captured CUA failures byte for byte (`579c857b…`, `57f39057…`, `c345a6e4…`, `4aef2d89…`). This identifies paragraph insertion, rather than a later project filter, as the sufficient cause. The Contact-only content filter and i18n anchor localizer are present in the full-chain probe; they do not account for these script changes.

Utility has a second formatting failure: the saved `<` comparisons let `wptexturize` encode later `&&` to `&#038;&#038;`. Its second script then fails at that token. That same script contains `updateHeader()` and `document.body.classList.toggle('us-at-cover', ...)`. A syntax error prevents the whole script from running, including the initial cover-class update. This explains why an unchanged raw class-setting statement can coexist with a local body lacking `us-at-cover`. The shared third script also suffers paragraph insertion. This is source/native-formatting evidence, not a new browser observation; the parent's previous Utility white-header captures do not validate the `us-at-cover` branch.

The existing `tools/migrate/repair-page-inline-blocks.py:28–70` already implements the narrow content repair: remove blank lines within inline script/style blocks, collapse the existing status bar line breaks, and reverse the five whitelisted, side-effect-free Utility comparisons. Applying its **pure** `repair()` function to the captured local content, with the existing pull URL substitutions reversed, yields current production `post_content` **exactly** for all four Service/Utility pages. Their visible prose also compares equal before this transformation. No new script algorithm or prose rewrite is required.

## All 50 published pages

The accompanying `local-render-published-pages-inventory.json` records every published page's ID, title, language, both raw `post_content` SHAs, and presence/full values for `_wp_page_template`, `_lc_livecanvas_enabled`, and `lc_use_template_of_slug`. Both sides contain the same 50 IDs, titles and language labels; all 50 sets of these native meta values match. The inventory is bound to its recorded local and production observation timestamps, not to any later parent-side synchronization.

The comparison uses all three existing `tools/pull/src/linker_pull/load.py:494–505` origin substitutions: plain URL, JSON-escaped URL, and URL-encoded URL. Comparing only the plain URL incorrectly inflates the difference count to 30. After all three substitutions:

| Actual difference | Pages | Evidence |
| --- | --- | --- |
| Stale inline-block repair | Service 2748/6700; Utility 1755/6917 | Existing pure repair gives exact production bytes after origin normalization. |
| Stale missing-backslash script | Privacy 1673/6827 | Production's one script with all 29 literal backslashes removed equals the local one exactly; markup/prose outside it matches after the separately identified public-email substitution. |
| Public support address pseudonym only | Contact 28/6907; Imprint 1672/6829; Refund 1038/6698; Terms 1674/6825 | Apart from the URL substitutions, the only change is `chester@de-linker.com` becoming `customer-42@example.test` in public text and its `mailto` link. |
| Additional public-email substitution on already listed pages | Privacy 1673/6827 | Same address substitution, independent of the script defect. |
| No other content difference | Remaining 36 pages | Exact equality under the three origin substitutions. |

Consequently there are six genuinely stale script pages, ten pages with the public-address substitution, and 14 distinct pages to align if both defects are repaired. No other current public-page prose or structure difference was found. Only published `page` records were inventoried; this does not certify posts, products, LC partials, account/order data, or the whole site.

The local snapshot marker reads `name=20261021-1023`, `taken=2026-10-21T02:26:29+00:00`, `loaded=2026-10-21T21:56:02+00:00`. This is consistent with loading a snapshot taken before the repairs. The exact historical writer that left these six pages stale was not independently established; the evidence establishes the current stale data and its exact production equivalent.

## Public-address anonymizer root cause and narrow repair seam

`tools/pull/src/linker_pull/anonymize.py:470–488` applies `scrub()` to string fields after each row's specific rule. `scrub()` at line 508 calls `Emails.replace_all()`. The latter reaches `Emails.replace():355–363`, which checks the customer-account map **before** `kept_as()` can preserve a company-domain mailbox. The `Emails.keeps()` method at lines 350–353 follows the same precedence. Thus the same published company address can be kept with no account collision and anonymized when that address also belongs to a non-staff customer account.

A pure, synthetic source-level probe with a customer account numbered 42 and the public company mailbox reproduces exactly `mailto:customer-42@example.test`; without that synthetic customer it preserves the public mailbox. An ordinary external customer-address control remains pseudonymized. No real customer table or credentials were read for this probe. The observed local replacement is therefore explained by this existing precedence; no claim is made about the current production account's role or ID from this synthetic test.

The smallest safe follow-on change should give the anonymizer a **public presentation field context**, initially the affected `wp_posts.post_content` of published pages, so a verified public company address in that field is preserved. It must continue scrubbing customer/guest addresses and credentials in the same content and must retain the current customer-account, customer-meta, HPOS/order, comments and arbitrary serialized-data rules. Moving the company-domain rule ahead of the customer map globally would also retain addresses in private customer records and would broaden the change beyond this public-content bug. Add a fixture where one company mailbox is simultaneously a customer-account address and a published Contact/legal address; assert the public text/mailto survives, while the account, billing/order, comments and unknown private fields remain pseudonymized. Existing `test_content_keeps_company_mailboxes_and_file_names` lacks that collision. No anonymizer source or tests were changed in this investigation.

## Smallest local synchronization, still not executed by this reviewer

The private `proposed-local-14-page-sync.private.json` is a concrete, `write=false` proposal for exactly the 14 distinct pages above. For every page it carries the captured local `before`, current production public `post_content`, all three production-to-local origin substitutions applied to `after`, both source hashes, the planned local hash, and an assertion that the native meta agrees. Preserve the raw production snapshot as the source of truth and compare the local `before` hash again immediately before any write. Do not write native meta: none of these fields differ.

The exact installed i18n plugin is `linker-i18n/linker-i18n.php`. Its `Jobs::before_post_saved():75–78` primes translation state and `Jobs::post_saved():100–109` queues published English saves. Neither method tests a generic `WP_IMPORTING`/CLI import guard. Merely setting such a flag, or passing `false` for WordPress's final after-hook flag while leaving the plugin loaded, does not suppress `pre_post_update`. Separately, `linker-tools/includes/Genie/PageCache.php:131–136` registers save hooks whose shutdown work can call its cache service. These are reasons to use the verified isolated native CLI invocation for a replica data restoration.

The observed read-only invocation is:

```text
/opt/homebrew/opt/php@8.3/bin/php -c /Users/chesterjohn/de-linker-local/sharedarchives/php.ini /opt/homebrew/bin/wp --path=/Users/chesterjohn/de-linker-local/sharedarchives/wordpress --skip-plugins --skip-themes eval-file <private-read-only-probe> <private-plan>
```

In this process both Linker i18n and Tools PageCache were absent, `pre_post_update` had zero callbacks, and the local MU mail-capture and external-HTTP isolation filters remained registered. `wp_filter_post_kses` was absent from `content_save_pre` on this exact CLI stack. The native dry roundtrip `wp_unslash(sanitize_post_field('post_content', wp_slash(after), id, 'db'))` matched all 14 proposed documents byte for byte, including both Privacy scripts' 29 backslashes. This probes native save filtering without invoking `wp_update_post` or changing the database.

After the parent's verified complete local database backup, reuse the existing transactional content writer `tools/migrate/repair-legal-script.php:29–94` with that `--skip-plugins --skip-themes` prefix: sorted row locks, exact `before` comparison, `wp_update_post(['ID' => id, 'post_content' => wp_slash(after)], true, false)`, immediate exact readback, rollback on any `Throwable`, and independent committed readback. The existing Python `invoke()` sends large payloads over STDIN; avoid placing two-megabyte page content in argv or shell strings. Readback must verify IDs, full content hashes/backslash counts, unchanged native meta/language pairing, and that the planned 36 other published pages were not altered. The writer updates only content and native modification bookkeeping; it must not overwrite titles, excerpts, slugs, language terms, credentials, customer data, or the instance's other current work.

This is a verified recommendation, not execution evidence. After synchronization, the parent still needs native HTTP script checks and actual EN/DE desktop/mobile Service and Utility interaction/cover/menu acceptance, plus Privacy icons/TOC/links/print acceptance. The pre-sync Utility captures that lacked `us-at-cover` remain excluded from coverage of that state. The parent's existing production 32-GET/70-unique-inline green result is a separate production observation; the local failure does not establish a production Service defect.

## Evidence entry points

Private fixed root: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/local-render-root-cause-20261022T072224138583Z/`.

| File | SHA-256 |
| --- | --- |
| `evidence-manifest.json` | `757586ddede290b21809411f3964365e4f93dbe51a2edc2937ab6dc6d1ca58ea` |
| `all-50-page-final-inventory.json` (identical bytes to accompanying public inventory) | `b4ac961e95dbce9af1bcf9de9453c58cb8a3ba4644d3d4e6f70a6b91b704cf86` |
| `production-different-published-pages.private.json` | `14795610654ea37ad6043fddca078ba67fe0a636d076380fd6e7bd1af7aa408f` |
| `proposed-local-14-page-sync.private.json` | `c49d563b8b961cc0a5ee04330a940d2e61aeb11edd3cf3e435043d4b08824b2a` |
| `native-stage-syntax-results.json` | `23c7b594a891187921c52f2226cae6f49676f300e5e54482660e3be29b22c233` |
| `save-filter-readonly-results.json` | `a271e5e771ab417045abbc974fc96bba10fc0d662e063a98e031710a4137f311` |
| `supplement-pull-email-precedence-counterexample.json` (separate supplemental file, added after the fixed manifest) | `b72645df508badfbb37a7dd4591bbba219610d80fe73965fedeb0ee1abf56750` |

Native stage inputs, extracted scripts, Node stderr and source-based comparison details are private files indexed by the fixed manifest. The public inventory contains hashes/meta, not page bodies. The supplemental anonymizer probe is intentionally identified separately rather than added to the already issued immutable manifest.
