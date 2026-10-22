# Genie retains the native footer runtime

Part of [normal Genie request and recovery acceptance](https://github.com/AssassinFlash/de-linker/issues/563).
The production normal-path check found a separate loading defect after the combined
`3c3c3c25` release: German page chrome remained German, but the Genie buttons could
become English. The page contained a dynamically inserted `i18n.min.js`, the Genie
locale data and entry, followed by the native versioned `wp-i18n-js` footer tag.
The later runtime replaced the instance holding the German strings. This was first
observed with the administrator session and subsequently on a normal guest load;
it was not an inference from a missing translation file. Native translation JSON
was present and contained `Senden`.

Core's actual `wp_print_footer_scripts` callback runs at `wp_footer` priority 20.
The dock loader now runs at 21. It describes printed native dependencies using
the global exports of the current WordPress build graph, while retaining every
fallback URL. The browser reuses an export only when that runtime actually exists;
a failed native request still enters the existing download/error/retry path.
Missing dependencies and the versioned Genie entry continue to load on demand. The native footer runtime therefore remains the instance used by
the entry and its translation payload. No interface copy, style, model route,
verification policy or provider budget changed.

## Verification

- The original source reproduced duplicate dependency loading. The PHP fixture
  now requires both fallback URLs and the printed native export hints; the actual
  loader JavaScript separately proves runtime reuse and download/retry recovery.
  The complete Entries group passes **32 tests / 186 assertions**, including the
  existing recoverable boot/keyboard-boundary test. Its first run lacked the new
  worktree's `jsdom`; installing the locked Node dependencies resolved that
  environment failure without changing a business assertion.
- WPCS for all three changed PHP files and the entire Tools PHPStan level 8 pass.
- Independent instance `g563i` uses the actual production snapshot
  `20261022-2159`, taken 14:04:08 UTC, with 212 published products, 2,756 attachments
  and all files present. Current presentation was applied and WindPress compiled
  from its native admin; the final `present` freshness check passes.
- Native hook readback confirms core 20 / dock 21. The actual signed-in German
  workspace has exactly one native i18n script, followed by the locale payload
  and the single Genie entry; `Neues Gespräch`, `Genie fragen` and `Senden` remain
  German after loading completes.
- [Eight native browser cases](browser-evidence.json) cover guest workspace and
  product-page helper, EN/DE, requested 1440×1000 and 390×844. Complete JPEGs have
  actual final DOM/image widths 1440 or 390.
  Every case has one i18n script and one versioned Genie entry, no horizontal
  overflow and the corresponding language. The mobile workspace screenshots use
  a fresh mobile navigation with the conversation rail closed; the rail was also
  opened/closed through its native button during inspection. All eight images
  were inspected. The temporary Chrome tab was closed and viewport override reset.

Independent Spec review of the first correction found that `done` proves a tag
was printed, not that its download succeeded. A new actual-loader JSDOM fixture
now covers reuse without a duplicate request, missing-runtime fallback, and a
failed fallback followed by the original successful Retry. Resources are supplied
only from memory; this is not browser network-failure or production evidence. The
exports follow the installed `@wordpress/dependency-extraction-webpack-plugin`
mapping; unknown handles retain their fallback. All eight normal native browser
cases were rerun after this correction.

The screenshots and DOM records are from the isolated snapshot, with native local
mail/HTTP guards. No provider response interception, paid question, business form
submission, production write or production test mail was used for these cases.
Failed IAB viewport overrides are retained privately as diagnostics and excluded
from this responsive evidence. Separate production EN/DE guest product questions
proved real responses before this narrow loading correction; they do not prove
this change deployed. Exact CI, independent Spec/Standards review, publication and
production loaded-script readback remain release gates.
