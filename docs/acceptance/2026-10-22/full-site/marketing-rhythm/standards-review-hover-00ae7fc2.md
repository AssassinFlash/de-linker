# CTA hover transition source Standards delta — 00ae7fc2

Verdict: **SOURCE PASS, bounded to the two new transition-property declarations and aggregate `00ae7fc26d8df2d5bc63c9e4ab99e7c82da7caf8e2e4fb8d261ad3e892e742ff`.** No actionable scope, cascade, native-control or steady-state regression was found in this narrow source change. The new compiled properties and thirty-six new runtime frames remain separate gates; a generating UI, paused response or old cache is not acceptance.

## Exact independently verified delta

I independently read and hashed `release-source-files.json` and its three current files, checked all byte counts, and recalculated its ordered `path + NUL + file SHA256 + LF` aggregate. All match:

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| `chrome.css` | 34623 | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `marketing-rhythm.css` | 4721 | `619fb5479df09038de581db648a4d7e168c203b60c546baa6b5588e8d1841dc7` |
| `hero-readability.css` | 621 | `034942b7178f8bc986b90441baa61cc738cb6bd1a80646b0f01510f47d312654` |

I compared directly with the retained d690 three-source snapshot at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-cta-transition-before-20261022T080931782242Z/`. Removing exactly the two new `transition-property: border-color, box-shadow;` lines and their one explanatory comment reproduces the old `marketing-rhythm.css` byte for byte. `chrome.css` and `hero-readability.css` are byte-identical to that snapshot. No steady-state color, font, width/height, spacing, focus outline, mobile breakpoint, header, hero backdrop or blur/filter declaration changed.

Independent fixed delta evidence:
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/hover-source-standards-20261022T081849651206Z/`.
`delta.diff` SHA256: `f51a3a2823b12c8dbd35ca60f102b8feb4b40462aac9657b822683de41fdd161`.

Only this report was written in the repository. No product/test changes, browser, instance operation, compilation or production activity was performed by this reviewer.

## Scope and project standards

Both declarations live inside existing WindPress rule bodies:

- `#installer-journal .lk-bottom-cta .lk-cta-actions > a`;
- `:is(#service-redesign #start, #tv-solution-v1 #contact) .lk-cta-actions > a`.

They select the direct anchor controls of the three demonstrated bottom/final CTA groups. They do not select other Installer query controls, other Service groups, the Application photo hero, a composer, account controls, footer navigation, language rail or open header menu. This change is not a generic `a:hover` reset.

The source continues through the existing unlayered WindPress volume. No PHP design, LC structure replacement, inline runtime style, snippet, event handler or second CSS pipeline is introduced. All copy and native hrefs stay in the existing page content. The same property list appears twice because the current two selector bodies express the three existing scope groups; that small repetition is readable and does not justify a broader refactor or a new cross-site selector abstraction. No actionable Fowler heuristic finding was identified.

## Native saved transition and cascade check

I independently read the actual saved Service/Application CSS from the fixed production public-page JSON used in the prior review, plus the retained Installer native public HTTP HTML at `public-performance-diagnostic-20261022T055254816868Z/04-{1,2}.html` and `05-{1,2}.html`. These are frozen filesystem reads, not fresh HTTP or production operations.

The four Installer HTML captures have the same combined inline stylesheet SHA256 `bb3ea7a7db62e223624b7b76adbfbbac59b145d241b5b18a74fa84660f5f7cf9`; the Service EN/DE saved styles have SHA `2907965ebec50b8943951ddd4f715ec160374f1119bb1bb460fd10024048f2c3`; Application EN/DE styles have SHA `a834d53f5ec79253d41e91436b00b8cb6d3fa19c35ec1d101e3de508d6561432`.

The relevant old transitions are:

| Group | Existing saved rule | Existing timing/property list | New specificity |
| --- | --- | --- | --- |
| Installer | `#installer-journal .lk-bottom-cta a`, with the native button-class group | `background .18s ease, color .18s ease, border-color .18s ease` | `(1,2,1)`; beats the relevant old `(1,1,1)` |
| Service | `#service-redesign :is(...,.lk-cta-actions a)` | `background .2s ease, color .2s ease, border-color .2s ease` | `(2,1,1)`; beats the old relevant `(1,1,1)` |
| Application | `#tv-solution-v1 :is(.lk-btn-primary,.lk-btn-teal)` | `background var(--proto-duration), color var(--proto-duration)` | `(2,1,1)`; beats `(1,1,0)` |

These are rules in saved `<style>` blocks, not an element-level transition style. The new more-specific longhand wins the `transition-property` component of the old shorthand even if that saved block is later in document order. The `:is()` sibling selector obtains the two native IDs from each branch; there is no specificity dependence on an invented wrapper. No stronger/important transition override or pseudo-element fill transition affecting these CTA backgrounds was identified in the inspected relevant native rules. Actual compiled/runtime inspection still must confirm this is the winning property list.

## Behavior judgment and remaining verification

The new list permits only `border-color` and `box-shadow` interpolation. Neither text `color` nor a background longhand is in that list. When the native hover/focus style changes the foreground and background, both therefore take their new values without independent timed color interpolation. This addresses the reported nine weak intermediate frames in the old thirty-six-frame capture set; it does not merely delay a screenshot to hide an ongoing low-contrast transition. Both hover entry and exit need new runtime observation.

Normal and steady-hover foreground/background declarations are unchanged. Existing duration and timing-function values remain in force for border/shadow feedback; important reduced-motion duration/transition rules are not weakened. The independent focus-visible outline declarations are unchanged and are not made to animate. No background blur/filter is added or removed by this delta, and the prior opaque-header/no-blur decision and photo-header backdrop remain exact previous bytes.

The source fix does not grant a steady-state contrast PASS or guarantee that another unexpected runtime rule cannot override it. The parent should verify native persistence/import/compiled cache bytes and then each actual CTA's computed `transition-property`; a generating state or paused CDP response cannot substitute for those readbacks. The old nine intermediate failures and original thirty-six frames must remain historical failure/transition evidence. The new thirty-six EN/DE × 1440/390 × state frames must be checked at real entry/exit as well as the endpoint, with normal captures cleared of prior hover/focus.

The d690 hero backdrop images remain valid evidence of that frozen background batch; this new aggregate is not retroactively assigned to them. Known Application hero secondary-link and Residential prompt-chip target-size work remains open under the same overall task. No complete page, whole hero, production deployment or full-site PASS is issued here.
