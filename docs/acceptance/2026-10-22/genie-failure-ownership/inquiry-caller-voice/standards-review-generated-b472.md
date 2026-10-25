# b472 generated outputs — independent Standards addendum

2026-10-22. **Bounded generated-output PASS.** No actionable generated-file, native asset-registration or catalog blocker found. This supplements the original b472 source review; it does not reapprove the author's handoff behavior or claim browser, 9270, physical voice, model/mail, CI, deployment or production acceptance.

All 19 product source hashes and 22 test/helper hashes independently remain identical to b472 (`b472f3259aeb32e17419745942c5653ffbbe82e1332914e385929300290dfb1a`). The original auxiliary PO hash is historical: its one approved reference-metadata update is explicitly part of the following 13-file generation delta, not silently folded into the old source report.

## Exact generation readback

The private before snapshot's 33 artifact hashes, current after snapshot's 33 hashes, and every one of the 13 changed-file after copies were independently verified against `retained-repair/generated/checks.json`. Recomputing the before/after difference yields exactly its 13 entries; no other mapped build/catalog file changed. All files below are under `plugins/linker-tools/`:

| Changed artifact | Verified after SHA-256 |
| --- | --- |
| `build/genie.asset.php` | `6a3e3b7414d0a95e091580498644bbb947bf6a204c8a896b9b7701705d8edf0f` |
| `build/genie.js` | `274b7b882cc9a92f2b26c1be5e3f7745cdce98767697eae20b59e067db2039dd` |
| `build/hero.asset.php` | `2a116f3a431cd4c63e3566840cde162f5a6905b3a7032c1684778fadfe1775f5` |
| `build/hero.js` | `068e5209310b475e21a0c830f96a9ee3b8327dfebebf468d9294ea1502902eef` |
| `build/inquiry-handoff.asset.php` | `6136874ae3d6c8c436afb6c957ea829fba16d4e1acf885b3dac735c2fe04fc93` |
| `build/inquiry-handoff.js` | `07df817b09007e2841e67e4d7cd5c1c355a5f3cc2821124977bf6b5349f812a3` |
| `build/manifest.json` | `90f757cf32028146293c120ebd739805444f2a8136e8a414d22eb42d45dcfe48` |
| `build/marketing.asset.php` | `beada248329b87fda668b70268fedd7f715d05d4e1f3c4265416ae9ee0ff0220` |
| `build/marketing.js` | `5f3f1ab71adcbf928e110f822bb2e29808c682636d8998e793179bb4ced7f71f` |
| `languages/linker-tools-de_DE_formal-6796211aef57736d0923df38ef696ad2.json` | `9e51c4f6604905489def0023448061253c9d2057c109b71aa7ed0da1a447f06e` |
| `languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json` | `208304568056df4f415df78ced301b0cb823354da25b780c10225bad27a8c932` |
| `languages/linker-tools-de_DE_formal.mo` | `c1a1c5ad5d2a4c749f91c2236c3adfd02f55e0dc2c3063e85869b33caf219ffd` |
| `languages/linker-tools-de_DE_formal.po` | `a61dfc2ae53d46fe9e30cebdbf58bfc102a3841f430189e6116c8f00fc5f2dd5` |

The full build manifest was independently checked by hashing every recorded file and reproducing its exact Git-tracked/unignored source/build selection: **106 inputs and 24 outputs match**, including the unchanged build configuration and package lock. This is a read-only check, not a second build. All four changed asset PHP files preserve their dependencies byte-for-byte after normalizing only their content-version strings. Existing `Assets::register()` still registers native `build/<entry>.js` with those dependencies/version and `wp_set_script_translations('linker-tools', languages/)`. Marketing keeps `wp-dom-ready`/`wp-i18n`; React apps keep WordPress's external React/element/i18n pipeline. All generated CSS remains unchanged.

## Translation preservation and runtime correspondence

Removing only `#:` reference lines from the before/after PO gives **byte-identical files**. Its only delta appends `build/genie.js build/hero.js` to the existing approved warning's reference line. Every msgid/msgstr, escape, punctuation and non-reference metadata byte is unchanged.

The independently hashed native extraction POT (`2120220204c6573308fcac9cfc2eb2256b0ca0362b96d4b9e133c233e266ab13`) references the warning at actual `build/genie.js:85` and `build/hero.js:67`; counting its occurrence in the actual bundles agrees. The two changed JSON filenames independently match MD5 of their native `source` paths, respectively `build/hero.js` and `build/genie.js`. Each adds only that one message, preserving every older translation and other top-level metadata. Decoding the compiled MO likewise yields **513 → 514 entries**, with the same one added warning and no changed/deleted old entry. Its translation matches the unchanged approved PO. No runtime JSON translation was invented by this repair.

## Verification provenance and limits

All 34 embedded raw log/report/exit records were verified against private original bytes, lengths and SHA-256; the separate native-warning block was verified in the hashed POT. The actual producer JSON reports confirm **642/642 full JS tests** and **7/7 catalog tests**, with no failed/pending tests. Recorded build, lint, types, format, manifest and native i18n gates exit 0. The original 128M extraction failure, wrong-working-directory catalog launch and three build performance warnings remain visible and are not converted into green runs.

Independently, the unchanged catalog consumer was executed from the isolated plugin cwd with the exact current generated build/languages files: **7 PASS**, log SHA `e1cf0d5db9c057e2474cd745cb33d1b0b0217c2d08bdfe557b9d68f55181b621`. No full-suite rerun, generator or source edit was performed by this reviewer.

Original snapshots/logs: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-generated-20261022T065019383587Z/`. Independent full 13-file before/after map, source/test readback, manifest counts and catalog log: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-standards-klyk754x/generated-b472-review-20261022T070446171953Z/`; readback SHA `0380dcec499baed80a2bab859574aadbcb3d209c2a45a8fbac5355f3958b559c`. This report is the sole repository edit for this addendum.
