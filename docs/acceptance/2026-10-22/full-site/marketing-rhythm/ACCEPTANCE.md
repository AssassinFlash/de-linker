# Marketing action spacing and header states

This batch follows the owner's 2026-10-22 request to inspect entire components, their sibling pages and interaction states, and to extend the active full-site goal to loading performance and functional completeness. It is one bounded batch of that active goal.

## Changes

- Installer EN/DE bottom actions previously used `lk-cta-actions`, while the saved page spacing rule only styled `lk-btn-row`. The production before captures measured 0px paragraph-to-actions spacing and about 2.8px between links. The actual action group now uses the existing 32px spacing token, a 12px gap, 48px minimum buttons, 14px labels and 16px explanatory text. Mobile actions stack at full available width. The long German heading keeps complete words and balanced lines.
- Service EN/DE contained a native `br` as a third grid item, leaving an empty row on mobile. That decorative break is hidden within this page's action group. Its buttons and explanatory text use the same spacing and readable sizes.
- Application EN/DE used a small secondary action with only a bottom border. Its existing native link now has a complete outline and the same readable label, spacing and minimum target. German desktop actions can wrap to a second line without truncation.
- The default sticky header uses a solid white surface instead of a translucent blurred one, so scrolled content does not show through its navigation.
- The complete native published-page inventory identified six saved photo header states: residential, commercial, utility, EPC, Application and About. Their language controls use a dark solid surface, a current-language underline and an inset focus ring that follows `currentColor`, including simultaneous hover plus keyboard focus.
- The existing mobile menu `data-open` state selects a white panel with the original colored logo and visible search, close and contact controls. Closing the menu restores the cover state. The closed photo header receives a dark translucent inner surface after review found white desktop navigation over a light photograph.

No page prose, link destination, product fact, privacy content, input handler or business route is changed by these two stylesheets. LiveCanvas still composes the pages; WindPress owns these styles. No snippets or new plugins are used.

## Current evidence boundaries

The current three-file release map is `release-source-files.json`, aggregate `00ae7fc2…`. `source-files.json` retains the earlier two-file d1 candidate, and `../hero-readability/source-files.json` retains the three-file d690 candidate. Their reports and failed frames remain historical evidence; later candidates do not overwrite their findings.

The three CTA groups have actual EN/DE x 1440/390 measurements and native JPEG captures. The `current-*` set uses the successfully persisted cache at 1792651246 and includes whole headings; `final-*` is the earlier action-focused framing. All measured groups have a 32px paragraph gap, 12px action gap, 16px body text, 14px link labels and 48px link height. This is component acceptance, not full-page or whole-site acceptance.

The final two-file source is `d1b740ea…`; native compile8c persisted cache 1792652406 (709,392 bytes, SHA256 `d3bc8291cbdc18d26f31348983673712c14466144b1ea1ccfb1725dc00a17bca`). Actual store and index HTTP 200 responses, the cache file and installed source hashes were verified. The 108 `accepted-*` header frames were independently opened: five exercised photo families have 90 bounded PASS states; the original 18 Utility frames are diagnostics because its old local script never entered the cover state. A separate settled Application frame closes a capture-during-transition query. See `visual-review-d1b740ea.md` for all exact hashes and limits.

After the local content alignment described below, 18 new `aligned-utility-*` frames actually reach `us-at-cover`, exercise EN/DE desktop and phone language hover/focus, menus, Escape close and scrolled states. These supplement the original evidence; the original diagnostic images and hashes remain unchanged. Independent visual disposition is recorded separately.

The broader body review found existing weak white text over bright photographs on EPC, Residential and Application. The separate stylesheet and its own source manifest, original 12 before captures, contrast envelope and review are under `../hero-readability/`. At that d690 addition, the two d1 stylesheets remained unchanged. Header acceptance does not certify the body text.

The three backdrop rules subsequently passed independent source and 12-pair actual before/after visual review at d690. All twelve native heading/action/cover geometries, texts and targets are identical before and after. The later hover correction leaves `chrome.css` and `hero-readability.css` byte-identical; it changes only two CTA transition-property declarations in `marketing-rhythm.css`.

Actual keyboard-plus-mouse captures exposed nine transient low-contrast color pairs while the original native buttons interpolated text and background through inverse colors. Those 36 d690 `release-*` frames remain diagnostics for that final-hover gate; one also had an already-hovered secondary action in its normal view. The repair preserves the existing normal and hover endpoint colors and restricts transitions to border/shadow, keeping text and background together. Both source reviews pass the exact 00ae delta.

Native compile10 completed in the official UI and persisted cache version 1792656909, 709,779 bytes, SHA256 `7b3b0ed61f18f3f6fd5897f844532ab4c342bc6138ef34388a49ce8e98c3d1cc`. All three installed volume hashes match the release map. HTTP status was not captured in this iteration because the native debugging connection was temporarily unavailable; no HTTP status is inferred. The actual file, new compiled property and later rendered winning styles establish separate readbacks. The temporary local login was visibly logged out and all 33 prior local cookie values were restored after reconnecting the tool.

The new 36 `hoverfix-*` JPEG/JSON pairs assert the actual 00ae/cache version, pure normal state (pointer outside the group), both native keyboard-plus-hover states with `:focus-visible`, 32px paragraph spacing, 12px gap, 16px body, 14px labels, 48px targets, loaded fonts, no admin bar and no horizontal overflow. All 72 links actually use `transition-property: border-color, box-shadow`. Forty-eight opaque foreground/background pairs have a minimum measured computed-color contrast of 4.8849:1; transparent pairs are excluded rather than treated as black. Independent actual-image disposition is recorded separately, and target-consumer navigation remains part of the active full-site goal.

`visual-review-hoverfix-00ae7fc2.md` independently opens all 36 new images and rehashes all 72 JPEG/JSON files. Its bounded visual conclusion is PASS for the recorded normal/hover/focus component views. It does not close downstream navigation, the known small hero secondary/prompt targets, complete-page review or production readback. Current CI and production deployment remain required.

The `compile3-rejected-*` and `compile6-rejected-*` files are failed or stale-cache diagnostics, not accepted results. Compiler 6 reached 'Cache built' without a confirmed 'Cache stored'; its old-file captures were explicitly rejected. Compiler 7 was verified through actual HTTP 200 store and index responses, file timestamp, bytes, SHA256 and browser computed styles. A Generate click or an enabled button is not the completion gate.

Production before photographs use the existing staff browser; local after photographs use a guest with loaded fonts. They support the recorded component changes, not a claim of identical-authentication whole-page pixel parity. The screenshots are native, unedited JPEGs.

## Other findings retained in the active goal

The local Service/Utility failure was traced to old saved script content, with no LC/template metadata drift across all 50 published pages. Utility's broken script was responsible for adding its cover class. The current production content already has the script repairs. A separate local-only alignment restored 14 pages to that production snapshot, using the existing native transaction, row locks, before-content comparison, `wp_slash()` and byte-exact readback with plugins/themes skipped. No metadata was written, no production page was changed and no new mail file was produced. Before that local write, a complete 40,943,659-byte database export was restored successfully into an isolated database (60/60 tables and all 14 planned before hashes). The initial export's GTID restore error was retained; a portable re-export with GTID statements disabled passed without changing the server's global GTID state.

An independent readback confirms 50/50 normalized pages equal the frozen production contents, only the planned 14 changed and the other 36 retained their hashes, all native metadata is unchanged, Privacy retains 29 backslashes per language, and all 18 scripts from Service/Utility/Privacy pass the actual native content-filter chain and syntax checking. See `local-render-root-cause.md` and `local-render-alignment-readback.md`. The public-company email anonymizer precedence defect is retained as a separate source correction in the active goal; customer data anonymization must remain intact.

The source inventory also exposes existing marketing promises about ordering through the account. Copy and function truth require the separate active full-site review against the owner's inquiry-only business contract; styling a button does not establish the promised business behavior.

## Release and rollback

Source review, native compilation, browser acceptance, CI, production release and production readback remain separate gates. Do not infer production completion from this file or a merged PR. The latest source and final browser evidence must pass before this batch is deployed.

The full local-only backup at `/Users/chesterjohn/de-linker-data/cutover-20261022-0541` has 39,129 files (4,397,067,359 bytes), with every size and SHA256 checked, gzip footer and options JSON validated, and zero mismatches. A code release additionally takes the native database snapshot and retains the previous atomic code release. The separate brand permalink option repair needs the full backup and exact option readback; its rollback restores the original existing empty string and flushes native rewrites. Neither the data repair nor production acceptance is claimed here.
