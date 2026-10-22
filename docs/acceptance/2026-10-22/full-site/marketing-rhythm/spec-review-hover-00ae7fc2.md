# Source Spec delta review — synchronous CTA hover colors

Verdict: **SOURCE PASS** for aggregate `00ae7fc26d8df2d5bc63c9e4ab99e7c82da7caf8e2e4fb8d261ad3e892e742ff`. The two scoped declarations address the observed low-contrast hover interpolation directly. Final compiled/runtime acceptance requires the new captures; the original d690 release frames remain historical and unaccepted for their intermediate contrast moments.

## Exact delta

I independently rehashed the current three-source manifest, checked byte counts and recomputed its ordered `path + NUL + SHA + LF` aggregate. The current `marketing-rhythm.css` is 4721 bytes, SHA `619fb5479df09038de581db648a4d7e168c203b60c546baa6b5588e8d1841dc7`. Removing exactly its two new `transition-property: border-color, box-shadow` declarations and one explanatory comment reproduces the frozen d690 file byte for byte. Frozen before source: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-cta-transition-before-20261022T080931782242Z/`.

`chrome.css` remains SHA `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9`; `hero-readability.css` remains SHA `034942b7178f8bc986b90441baa61cc738cb6bd1a80646b0f01510f47d312654`. Both are exact before/current byte matches.

The only changed rule bodies are at `marketing-rhythm.css:23–34` and `:65–78`:

- `#installer-journal .lk-bottom-cta .lk-cta-actions > a`
- `:is(#service-redesign #start, #tv-solution-v1 #contact) .lk-cta-actions > a`

These are the existing three actual CTA groups, containing the two links already captured in each EN/DE page. They do not select the Installer's other query buttons, the Service page's other button groups, the Application hero, account controls, a composer, footer navigation, language rail, or header/menu controls. No new hover/focus selector, text, href, markup, geometry or final-state color was introduced.

## Existing saved-page transition and cascade

The original page CSS is in saved `<style>` blocks, rather than per-link `style` attributes. I independently read the Installer's native public HTTP HTML captured before this delta (`public-performance-diagnostic-20261022T055254816868Z/04-{1,2}.html` and `05-{1,2}.html`), and Service/Application raw saved page CSS in the prior fixed production public-page snapshot. The relevant original rules are:

| Family | Original transition | Original maximum relevant selector specificity | New selector specificity |
| --- | --- | --- | --- |
| Installer | `background .18s ease, color .18s ease, border-color .18s ease` on native button group / `.lk-bottom-cta a` | `(1,1,1)` | `(1,2,1)` |
| Service | `background .2s ease, color .2s ease, border-color .2s ease` on the existing `:is(...,.lk-cta-actions a)` group | `(1,1,1)` | `(2,1,1)` |
| Application | `background var(--proto-duration), color var(--proto-duration)` on `.lk-btn-primary` / `.lk-btn-teal` | `(1,1,0)` | `(2,1,1)` |

The two-ID specificity in the sibling rule comes from each `:is()` branch's native section root plus its `#start`/`#contact` ID. Thus the new longhand wins the original background/color transition shorthand even if that saved style is encountered later. No stronger or important transition-property override was found for these targeted links. The Service reduced-motion rule's important `.01ms` duration remains intact, because this delta changes only `transition-property`.

The original 36 capture JSON files also bind the actual two-link groups and EN/DE routes at both widths. Reusing their existing scoped rule bodies avoids expanding this repair to other native controls. This source delta uses the same unlayered WindPress volume path previously reviewed; actual compiled imports and computed transition properties remain a runtime readback gate.

## Behavior and scope judgment

Restricting the animated property list excludes both `color` and every `background` longhand. On hover entry and hover exit, those two values therefore switch as part of the same style update rather than crossing independently through pale intermediate pairs. The native normal and steady-hover foreground/background declarations are unchanged. This addresses the real low-contrast transition observed in the original captures, not merely the time at which screenshots are taken.

The existing transition durations and easing declarations are not replaced. They apply to the permitted border-color and box-shadow changes; they cannot animate text or background because those properties are absent from the list. The independent focus-visible outline declarations are unchanged and remain immediate. No size, padding, margin, display, flex wrapping, label font, border width, image crop or layout property changed. No motion or timing preference is weakened.

There is no source blocker in this narrow repair. After official compile10, verify that every targeted link's computed `transition-property` is the new two-item list, normal has no leftover hover/focus, and both links' colors remain legible during actual entry/exit as well as at the endpoint. Recheck all 36 intended EN/DE/width/state captures and keep the old 36 as the recorded before/failure evidence. If a new frame still has a weak pair, it must remain a finding rather than inherit this source PASS.

This review performed only filesystem/source/hash/HTML reads and pure comparisons. It did not compile, open a browser, operate the local instance, change application source/tests, call a model/mail endpoint, or deploy. Only this new report was written. It does not certify clicks, destination consumers, complete pages, production deployment or the full site.
