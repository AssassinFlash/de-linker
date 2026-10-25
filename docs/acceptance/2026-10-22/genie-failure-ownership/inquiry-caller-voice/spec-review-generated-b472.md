# b472 build/i18n — independent generated-delta review

**Bounded generated-output PASS.** The reviewed ordinary ownership source remains `b472f3259aeb32e17419745942c5653ffbbe82e1332914e385929300290dfb1a`; no product or test semantics changed. This does not establish browser delivery, model/microphone behavior, runtime 9270, deployment or production acceptance.

Scope: the 13 changed generated/translation artifacts in the producer’s exact before/after map, plus source-preservation and dictionary consumption checks. Private exact evidence: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-generated-20261022T065019383587Z/`. Repository evidence is under [retained-repair/generated](pending-voice-variants/retained-repair/generated/README.md). Only this report was written; no product, test, PO, build, instance or original evidence was modified. No dependency was installed, generator run, instance called or browser opened by this review.

## Exact artifact/source verification

All 13 original before files, final after files, and current worktree outputs were independently hashed against the recorded map. All recorded `generated_after` outputs also match current bytes. The 19 product source and 22 test/helper hashes were checked again and remain exactly the approved b472 values. The PO metadata change is accounted for separately below rather than called byte-identical.

The build manifest was independently read and all **106 source inputs and 24 build output SHA values** compared with actual files. They all match. Manifest SHA-256 is `90f757cf32028146293c120ebd739805444f2a8136e8a414d22eb42d45dcfe48`. This is an additional read-only byte check, not a rerun of the build or a claim that all 106 inputs were newly changed in this batch.

| Changed artifact | Before → after SHA prefix |
| --- | --- |
| `build/genie.asset.php` | `2e9490809b85` → `6a3e3b7414d0` |
| `build/genie.js` | `0727ed1cccd8` → `274b7b882cc9` |
| `build/hero.asset.php` | `7af79bb6bad6` → `2a116f3a431c` |
| `build/hero.js` | `430c5bc0798d` → `068e5209310b` |
| `build/inquiry-handoff.asset.php` | `fdb4f24292ef` → `6136874ae3d6` |
| `build/inquiry-handoff.js` | `474e0ebb4338` → `07df817b0900` |
| `build/manifest.json` | `8cb65a89a88d` → `90f757cf3202` |
| `build/marketing.asset.php` | `7617ab2655e7` → `beada248329b` |
| `build/marketing.js` | `71bb04764618` → `5f3f1ab71adc` |
| `languages/linker-tools-de_DE_formal-6796211aef57736d0923df38ef696ad2.json` | `58b039075152` → `9e51c4f66049` |
| `languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json` | `1ba67644bd45` → `208304568056` |
| `languages/linker-tools-de_DE_formal.mo` | `ec747615ce8c` → `c1a1c5ad5d2a` |
| `languages/linker-tools-de_DE_formal.po` | `f72310a2be2e` → `a61dfc2ae53d` |

Full 64-character before/after values and original bytes remain in the private map/snapshots and the repository `checks.json`; the table shortens hashes only for readability. The unchanged generated outputs are not presented as part of the 13-file delta.

## PO, native source references and actual catalogue consumption

The PO diff is exactly one reference line: `src/genie/App.tsx src/hero/Hero.tsx` gains `build/genie.js build/hero.js`. Independently removing only `#:` lines from before/after PO leaves identical bytes. All msgid/msgstr values and non-reference metadata are therefore unchanged; no new English/German wording was authored or silently retranslated.

The preserved native WP-CLI extracted POT actually identifies the warning in `build/genie.js:85` and `build/hero.js:67`. Those references correspond to compiled entries that contain the warning, not an arbitrary catalogue-name workaround. The unchanged native Assets producer calls `wp_set_script_translations($handle, 'linker-tools', ...languages)`.

Independently computing the native relative-entry MD5 maps `build/genie.js` to `c2be3a742ec1f5e619cd2beb8d234138` and `build/hero.js` to `6796211aef57736d0923df38ef696ad2`. Both actual JSON files identify the correct `source` entry. Comparing their decoded message maps with the exact before files finds one addition each, no deletions and no changed existing translations: the approved unsaved-question warning. Loading the before/after MO through Python’s GNUTranslations gives that same sole addition, with no removed/changed prior translation.

For a direct consumer check, this reviewer loaded each final JSON separately into the installed actual `@wordpress/i18n` library (`resetLocaleData`, `setLocaleData`, then `__`). Both entry catalogues return exactly:

> Ihre Frage konnte nicht gespeichert werden. Wenn Sie diese Seite neu laden oder verlassen, kann sie verloren gehen.

This verifies actual client-library catalogue consumption rather than only finding a key in JSON. It is not a WordPress browser script-injection/arrival test, which remains with runtime acceptance. The warning’s previously reported generated-dictionary gap is closed for these artifacts.

## Command evidence checked, without rerunning generation

Every listed raw command-log SHA and `.exit` value was independently compared with the producer records. The final JSON reports were parsed directly: **642 tests pass / 0 fail / 0 pending across 63 files**, and the correctly launched standalone catalogue test is **7/7 pass**. Successful logs also record full-plugin ESLint, TypeScript, formatting, build-manifest, native i18n coverage and validity checks. The tools PO has no source gap/JSON problem; repository coverage output retains its stated existing commerce exemptions rather than claiming every other catalogue has no exemptions.

Earlier failures remain correctly classified and preserved: initial generation exposed the one missing approved warning; the broad native POT extraction exhausted the process’s default 128M parser memory; a catalogue run launched from repository cwd failed relative-path reads. Scoped native extraction with a process-local 1G bound and unchanged catalogue tests run from the required plugin cwd passed. No assertion/checker weakening or global PHP/configuration change was found. The successful build’s three webpack size/performance warnings remain visible; no unrelated performance redesign is claimed.

No generated delta introduces new ownership/routing logic beyond the approved source. The b472 source PASS and this generated-output PASS are separate from final real-bundle EN/DE desktop/mobile visual/consumer validation and production readback. Independent readback summary is retained at `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/generated-spec-b472-sk5ee1ae/independent-readback.json`.
