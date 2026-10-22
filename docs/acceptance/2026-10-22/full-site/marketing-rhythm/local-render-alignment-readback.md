# Independent local content alignment readback

Verdict: **PASS for the named local public-page data and native script-syntax boundaries.** This is a new post-alignment observation. The earlier `local-render-root-cause.md` and its before-state inventory remain unchanged.

At `2026-10-22T07:28:04+00:00`, the reviewer independently read all 50 published `page` records from `sharedarchives` (`http://127.0.0.1:9290`) and compared them with the production public-page snapshot frozen at `2026-10-22T07:16:17+00:00`. No new production fetch is implied. The comparison reverses exactly the existing pull's three production/local origin substitutions: plain, JSON-escaped, and URL-encoded. It does not normalize prose, JavaScript, whitespace, backslashes, or public email addresses.

| Boundary | Independent result |
| --- | --- |
| Published page ID set | Same 50 IDs |
| ID/title/language | 50/50 identical to the frozen production snapshot |
| Complete `post_content` after the three origin substitutions | 50/50 SHA matches |
| `_wp_page_template`, `_lc_livecanvas_enabled`, `lc_use_template_of_slug` | Presence and complete values unchanged from the pre-alignment local read for all 50 pages; also equal to the frozen production values |
| Pages whose raw local content SHA changed | Exactly the 14 planned IDs: 28, 1038, 1672, 1673, 1674, 1755, 2748, 6698, 6700, 6825, 6827, 6829, 6907, 6917 |
| Other 36 published pages | Original local raw SHA unchanged |
| Public content matching `customer-\d+@example.test` | 0 occurrences across all 50 pages |
| Privacy literal backslashes | EN1673: 29; DE6827: 29 |

The public `local-render-alignment-readback.json` records every ID, title, language, current raw/normalized SHA, frozen production SHA, native-meta comparisons, changed-page flag, and public-email/backslash counts. Its SHA-256 is `8c8dce55faf7e46550c5a22036e6922794f1c1be6433db141cd2a8aa01440f4e`. This checks the three specifically inventoried native template/LC keys, not every unrelated WordPress metadata key.

## Actual native filter and syntax consumers

For each of the six repaired script pages, a separate native WP-CLI process selected the real saved page context, ran installed LiveCanvas's native `lc_alter_content_filters()` handler, and applied the full installed `the_content` chain. Scripts were then extracted to private files and checked with the actual `node --check` command. There was no content update and no browser execution.

| Page | Script count | Full native chain syntax | Full-chain script bytes equal raw saved script bytes | Saved script bytes equal frozen production |
| --- | ---: | --- | --- | --- |
| Service EN2748 | 5 | 5/5 pass | Yes | Yes |
| Service DE6700 | 5 | 5/5 pass | Yes | Yes |
| Utility EN1755 | 3 | 3/3 pass | Yes | Yes |
| Utility DE6917 | 3 | 3/3 pass | Yes | Yes |
| Privacy EN1673 | 1 | 1/1 pass | Yes | Yes |
| Privacy DE6827 | 1 | 1/1 pass | Yes | Yes |

All 18 scripts pass after the real native filtering chain. Native LC remains false and `wpautop` remains registered at priority 10 on these six pages. Thus the current success does not depend on newly enabling LC or removing WordPress formatting. Utility's repaired cover/stage script now survives these native filters without paragraph insertion or encoded `&&`. This closes the previous native-render syntax blocker; it does not prove the browser executed its `us-at-cover` branch or that its interactive states are visually correct.

## Parent execution record and independent boundary

The parent's `sharedarchives-content-alignment-20261022T072234522131Z/alignment-result.json` reports completion at `2026-10-22T07:25:51.760454+00:00`, saved14/readback14, no meta writes, no production writes, and zero added mail files. Its exact SHA is `de4f662a5326c9809a23b78ec477a32bf162cd911e79e62f1c96edcd4e5f9e87`. The reviewer checked that its 14 before/after hashes match the previously frozen proposal exactly.

The reviewer also independently hashed the parent's `database-portable.sql`: actual size `40,943,659` bytes and SHA `da46d1f6f502835a50ee07e30ecec552e4dfd28fd456606353991f6895d6f0cf` match the execution record. The record states that the first GTID-bearing dump failed isolated restoration before content writes, and that an explicit `set-gtid-purged=OFF` export then restored 60/60 tables and the 14 pre-write content hashes. The restore exercise and mail-file delta are parent-collected evidence; this reviewer did not re-import any database or repeat those operations.

Only read-only local CLI probes, file/hash comparisons, and script syntax checks were performed by this reviewer. No instance data, option, metadata, application source, model, email, browser, or production operation was changed or invoked by the reviewer. Evidence files and this new report are the only reviewer writes.

The two marketing CSS sources still match the previously reviewed aggregate `d1b740ea801a440ba3a05ab60026a000ebfb06cd64484d53cb3467ee9fcd34e4`:

- `chrome.css`: `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9`
- `marketing-rhythm.css`: `710fb37175f4b157816880e151fd9796b0e5e68ae5c3408f71a75aa0ecc80139`

No new CSS source review or compiled-runtime claim follows from the content synchronization.

## Evidence and remaining acceptance

The independent post-alignment evidence root is `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/local-render-alignment-readback-20261022T072803676245Z/`.

| Entry | SHA-256 |
| --- | --- |
| `manifest.json` | `b6066aa666ed3923bc18051142756db87ff3c52674449993f9c7bab852ebff44` |
| `summary.json` | `6be620d24a1619dca6b7c9b3d72deb1fa8acc195079e7da29c9f120d43771025` |
| `all-50-page-comparison.json` / identical public adjacent readback JSON | `8c8dce55faf7e46550c5a22036e6922794f1c1be6433db141cd2a8aa01440f4e` |
| `native-script-syntax-results.json` | `3935f028647090ca8601d3072f5b09d28f1e52b793acb81a935efcdcbb0678b3` |

Raw native collectors, their JSON inputs/results, extracted script files and stderr are indexed by that manifest. Before-state production/local snapshots and the proposed 14-page synchronization remain in the separate prior fixed investigation directory.

The parent still owns actual EN/DE desktop/mobile Service/Utility interactions and cover/menu state checks, and Privacy icons, contents navigation, chapter links and print acceptance. No browser, visual, physical voice, form submission, production parity, or whole-site completion is certified by this narrow readback. The previous Utility screenshots without `us-at-cover` remain historical captures of the normal-header state.
