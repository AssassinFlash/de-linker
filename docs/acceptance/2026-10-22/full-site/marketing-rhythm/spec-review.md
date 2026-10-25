# Marketing rhythm — independent Spec review

Reviewed on 2026-10-22 against `9aa0ffe43d65e3ed822ce085e346941c9953a5ef`. Scope is the two CSS sources below. No product source, instance, browser, build, or production was changed by this review; this report is the sole output.

| Source | SHA-256 |
| --- | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | `412b03a5ac41da39d616a6c3cbe0c46469d8a2303a23ecfc40ef0f1a83cbd542` |

**Bounded PASS: no source-level Spec blocker in this batch; Installer CTA saved-view visual PASS.** This is not full-site, photo-header, navigation-consumption, or production acceptance.

## Scope and behavior

The only change to existing chrome is the default sticky header background becoming opaque white and removal of the two backdrop-filter declarations (`chrome.css:25–26`). Sticky positioning, admin-bar offsets, navigation composition, links, and dimensions are unchanged. The intent addresses content showing through the navigation surface. Because this selector is global, the four Installer captures alone cannot establish photo-led Residential/Commercial page parity or close their previously observed header contrast issue; page-specific overrides may be in saved page content and require actual runtime readback.

The new stylesheet is limited to `#installer-journal .lk-bottom-cta`. It targets the actual `.lk-cta-actions` rather than an unrelated button-row class. It preserves native anchor semantics and destinations and adds no JavaScript, PHP layout, text rewrite, or new business behavior. It reuses existing spacing/focus tokens, permits natural heading wrapping, maintains readable 16px/1.65 paragraphs, and gives the two native links 48px minimum height. Under 640px the links form a full-width column; at larger widths wrapping is allowed rather than fixed widths or clipped labels. This is consistent with the user-authorized visual repair and the existing LC/WindPress design ownership.

## Saved-view evidence actually inspected

All seven following original JPEGs were individually opened, with their corresponding JSON readbacks inspected. Evidence source: `cua-local-20261022T0602/`, local URL origin `http://127.0.0.1:9290`, viewport height 1000, fonts loaded, logged-out state, compiled CSS URL version `1792648845`.

| Views | Assessment |
| --- | --- |
| [EN 1440](cua-local-20261022T0602/en-1440.jpg), [EN 390](cua-local-20261022T0602/en-390.jpg) | Heading/paragraph/actions have distinct spacing. Primary filled and secondary outlined links communicate hierarchy; labels are complete. Desktop links are 48px tall; phone links are 354×48px with 12px separation. |
| [DE 1440](cua-local-20261022T0602/de-1440.jpg), [DE 390](cua-local-20261022T0602/de-390.jpg) | Long heading wraps at word boundaries, with no cut-off or collision. Phone five-line heading remains readable; paragraph and buttons are separate. Both phone links are 354×48px with complete German labels. Existing paragraph hyphenation is visible and does not lose letters. |
| [Primary focus](cua-local-20261022T0602/de-1440-primary-focus.jpg), [secondary focus](cua-local-20261022T0602/de-1440-secondary-focus.jpg) | Each active control has a visible 2px teal outline offset by 2px, without shifting or clipping the control. The pointer happens to hover the secondary link in the primary-focus capture; JSON distinguishes hover from keyboard focus. |
| [Primary settled hover](cua-local-20261022T0602/de-1440-primary-hover-settled.jpg) | Primary changes to a white background with teal text/border; the secondary control separately retains keyboard focus. The stable result is readable and remains a clear button. The earlier transitional hover record is not used as the final color verdict. |

All four baseline readbacks show no horizontal document overflow; the actual paragraph-to-action gap is 32px from the installed spacing token (not the fallback literal). The header is opaque white with no backdrop filter, at 89px desktop/81px phone, without text showing through it in these Installer captures. These numeric observations support, but do not replace, the visual inspection above.

Native destination readbacks remain `/solution-configurator/` and `/my-account/` in EN, and `/de/loesungskonfigurator/` and `/de/mein-konto/` in DE. No actual destination click/arrival, account registration, or configurator flow was performed by this review. No new customer copy was introduced, so this delta does not create a new copy-review surface.

## Acceptance boundary still open

Before treating the global header repair as accepted across the site, inspect EN/DE × 1440/390 Residential and Commercial photo headers at the top and while scrolled, including the effective computed background/filter, text contrast, and mobile navigation overlay. The Installer captures do not prove those states. Other page families, intermediate widths, browser zoom, print, and production deployment/readback are outside this small batch and remain separate gates. The user’s broader full-site visual audit is not complete on the strength of this PASS.
