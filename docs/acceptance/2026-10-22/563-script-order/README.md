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
The dock loader now runs at 21 and omits dependency handles already in the native
`WP_Scripts::done` list. It still loads missing dependencies and the versioned Genie
entry on demand. The native footer runtime therefore remains the instance used by
the entry and its translation payload. No interface copy, style, model route,
verification policy or provider budget changed.

## Verification

- The added regression failed on the unchanged source: the loader included all
  five core dependencies even when WordPress had already printed them. After the
  fix, the complete Entries group passes **31 tests / 179 assertions**, including
  the existing recoverable boot/keyboard-boundary JavaScript test. Its first run
  lacked the new worktree's `jsdom`; installing the locked Node dependencies
  resolved that environment failure without changing a business assertion.
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
  actual DOM/image widths 1425, 375 or 390 (the open helper hides the scrollbar).
  Every case has one i18n script and one versioned Genie entry, no horizontal
  overflow and the corresponding language. The mobile workspace screenshots use
  a fresh mobile navigation with the conversation rail closed; the rail was also
  opened/closed through its native button during inspection. All eight images
  were inspected. The temporary Chrome tab was closed and viewport override reset.

The screenshots and DOM records are from the isolated snapshot, with native local
mail/HTTP guards. No provider response interception, paid question, business form
submission, production write or production test mail was used for these cases.
Failed IAB viewport overrides are retained privately as diagnostics and excluded
from this responsive evidence. Separate production EN/DE guest product questions
proved real responses before this narrow loading correction; they do not prove
this change deployed. Exact CI, independent Spec/Standards review, publication and
production loaded-script readback remain release gates.
